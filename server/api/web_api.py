"""
Web API for Filmeto

FastAPI-based web interface for the Filmeto API.
Provides REST endpoints and Server-Sent Events for streaming.
"""

import json
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from server.api.filmeto_api import FilmetoApi
from server.api.types import (
    FilmetoTask, TaskProgress, TaskResult, ToolType, ResourceInput,
    ValidationError, PluginNotFoundError, PluginExecutionError, TimeoutError as TaskTimeoutError
)


# Pydantic models for API
class TaskRequest(BaseModel):
    """Request model for creating a task"""
    tool_name: str = Field(..., description="Tool to use (e.g., 'text2image')")
    plugin_name: str = Field(..., description="Plugin name to execute")
    parameters: dict = Field(..., description="Tool-specific parameters")
    resources: list = Field(default_factory=list, description="Input resources")
    timeout: int = Field(default=300, description="Timeout in seconds")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class TaskResponse(BaseModel):
    """Response model for task creation"""
    task_id: str
    status: str
    message: str


class ToolInfo(BaseModel):
    """Tool information"""
    name: str
    display_name: str


class PluginInfo(BaseModel):
    """Plugin information"""
    name: str
    version: str
    description: str
    tool_type: str
    engine: str
    author: str


class ErrorResponse(BaseModel):
    """Error response"""
    code: str
    message: str
    details: dict = {}


# Create FastAPI app
app = FastAPI(
    title="Filmeto API",
    description="Unified API for AI model services",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Filmeto API
filmeto_api: Optional[FilmetoApi] = None


@app.on_event("startup")
async def startup_event():
    """Initialize API on startup"""
    global filmeto_api
    filmeto_api = FilmetoApi()
    print("Filmeto API started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if filmeto_api:
        await filmeto_api.cleanup()
    print("Filmeto API stopped")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Filmeto API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/v1/tools", response_model=list[ToolInfo])
async def list_tools():
    """
    List all available tools.
    
    Returns:
        List of available tools with their information
    """
    try:
        tools = filmeto_api.list_tools()
        return tools
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/plugins", response_model=list[PluginInfo])
async def list_plugins():
    """
    List all available plugins.
    
    Returns:
        List of available plugins with their information
    """
    try:
        plugins = filmeto_api.list_plugins()
        return plugins
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/plugins/by-tool/{tool_name}", response_model=list[PluginInfo])
async def get_plugins_by_tool(tool_name: str):
    """
    Get all plugins supporting a specific tool type.
    
    Args:
        tool_name: Tool type (e.g., "text2image")
    
    Returns:
        List of plugins supporting the tool
    """
    try:
        plugins = filmeto_api.get_plugins_by_tool(tool_name)
        return plugins
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Create and start a new task.
    
    Args:
        task_request: Task creation request
    
    Returns:
        Task response with task_id
    """
    try:
        # Convert request to FilmetoTask
        task = FilmetoTask(
            tool_name=ToolType(task_request.tool_name),
            plugin_name=task_request.plugin_name,
            parameters=task_request.parameters,
            resources=[ResourceInput.from_dict(r) for r in task_request.resources],
            timeout=task_request.timeout,
            metadata=task_request.metadata
        )
        
        # Validate task
        is_valid, error_msg = filmeto_api.validate_task(task)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Note: Task execution should be done via streaming endpoint
        # This endpoint just validates and returns task_id
        
        return TaskResponse(
            task_id=task.task_id,
            status="created",
            message="Task created successfully. Use /api/v1/tasks/{task_id}/stream to execute."
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/execute")
async def execute_task_stream(task_request: TaskRequest):
    """
    Execute a task with Server-Sent Events streaming.
    
    This endpoint creates and executes a task, streaming progress updates
    and the final result using Server-Sent Events (SSE).
    
    Args:
        task_request: Task execution request
    
    Returns:
        StreamingResponse with SSE data
        
    Example:
        ```javascript
        const eventSource = new EventSource('/api/v1/tasks/execute', {
            method: 'POST',
            body: JSON.stringify({...})
        });
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'progress') {
                console.log('Progress:', data.percent);
            } else if (data.type === 'result') {
                console.log('Result:', data);
            }
        };
        ```
    """
    try:
        # Convert request to FilmetoTask
        task = FilmetoTask(
            tool_name=ToolType(task_request.tool_name),
            plugin_name=task_request.plugin_name,
            parameters=task_request.parameters,
            resources=[ResourceInput.from_dict(r) for r in task_request.resources],
            timeout=task_request.timeout,
            metadata=task_request.metadata
        )
        
        # Create event generator
        async def event_generator():
            try:
                async for update in filmeto_api.execute_task_stream(task):
                    if isinstance(update, TaskProgress):
                        # Send progress update
                        data = update.to_dict()
                        data['_type'] = 'progress'
                        yield f"data: {json.dumps(data)}\n\n"
                    elif isinstance(update, TaskResult):
                        # Send final result
                        data = update.to_dict()
                        data['_type'] = 'result'
                        yield f"data: {json.dumps(data)}\n\n"
            except ValidationError as e:
                error_data = {
                    "_type": "error",
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            except PluginNotFoundError as e:
                error_data = {
                    "_type": "error",
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            except PluginExecutionError as e:
                error_data = {
                    "_type": "error",
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            except TaskTimeoutError as e:
                error_data = {
                    "_type": "error",
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            except Exception as e:
                error_data = {
                    "_type": "error",
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "details": {}
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering in nginx
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get current status of a task.
    
    Args:
        task_id: Task identifier
    
    Returns:
        Task status information
    """
    try:
        status = await filmeto_api.get_task_status(task_id)
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
