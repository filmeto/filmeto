"""
Web API for Filmeto

FastAPI-based web interface for the Filmeto API.
Provides REST endpoints and Server-Sent Events for streaming.
"""

import json
import asyncio
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from server.api.filmeto_api import FilmetoApi
from server.api.types import (
    FilmetoTask, TaskProgress, TaskResult, Capability, ResourceInput,
    ValidationError, ServerNotFoundError, ServerExecutionError, TimeoutError as TaskTimeoutError
)
from server.api.chat_types import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelListResponse,
)


# Pydantic models for API
class TaskRequest(BaseModel):
    """Request model for creating a task"""
    capability: str = Field(..., description="Capability to use (e.g., 'text2image')")
    server_name: str = Field(..., description="Server name to execute")
    parameters: dict = Field(..., description="Capability-specific parameters")
    resources: list = Field(default_factory=list, description="Input resources")
    timeout: int = Field(default=300, description="Timeout in seconds")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class TaskResponse(BaseModel):
    """Response model for task creation"""
    task_id: str
    status: str
    message: str


class CapabilityInfo(BaseModel):
    """Capability information"""
    name: str
    display_name: str


class ServerInfo(BaseModel):
    """Server information"""
    name: str
    version: str
    description: str
    capability_type: str
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
    version="2.0.0"
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
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/v1/capabilities")
async def list_capabilities(capability_type: Optional[str] = None):
    """
    List all capability instances.

    Capabilities represent server:model combinations that provide specific
    AI services. Each capability has a unique key in "server:model" format.

    Args:
        capability_type: Optional filter by capability type (e.g., "text2image")

    Returns:
        List of capability instances with descriptions for LLM selection

    Example:
        GET /api/v1/capabilities?capability_type=text2image
    """
    try:
        capabilities = filmeto_api.list_capabilities(capability_type)
        return {
            "capabilities": capabilities,
            "total": len(capabilities),
            "capability_type_filter": capability_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/capabilities/groups")
async def list_capability_groups():
    """
    List capabilities grouped by capability type.

    Returns all capabilities organized by their type (text2image, image2video, etc.)
    with each group containing available server:model options.

    Returns:
        List of capability groups with their instances
    """
    try:
        groups = filmeto_api.get_capability_groups()
        return {
            "groups": groups,
            "total_groups": len(groups)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/capabilities/{key}")
async def get_capability(key: str):
    """
    Get a specific capability instance by key.

    Args:
        key: Capability key in "server:model" format
             (e.g., "bailian-prod:wanx2.1-t2i-turbo")

    Returns:
        Capability instance details including description for LLM selection
    """
    try:
        capability = filmeto_api.get_capability(key)
        if not capability:
            raise HTTPException(
                status_code=404,
                detail=f"Capability '{key}' not found"
            )
        return capability
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/capabilities/select/{capability_type}")
async def get_capability_selection_context(
    capability_type: str,
    user_requirement: Optional[str] = None
):
    """
    Get context for LLM to select appropriate capability.

    This endpoint returns structured information that can be used
    by an LLM to select the most appropriate capability instance
    based on user requirements.

    Args:
        capability_type: Capability type needed (e.g., "text2image")
        user_requirement: Optional user requirement description

    Returns:
        Structured context for LLM-based capability selection
    """
    try:
        context = filmeto_api.get_capability_selection_context(
            capability_type,
            user_requirement or ""
        )
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Selection API endpoints
# ---------------------------------------------------------------------------

class SelectionRequest(BaseModel):
    """Request model for server/model selection."""
    mode: str = Field(default="auto", description="Selection mode: auto, server_only, exact")
    server: Optional[str] = Field(default=None, description="Server name (for server_only/exact modes)")
    model: Optional[str] = Field(default=None, description="Model name (for exact mode or preference)")
    tags: Optional[List[str]] = Field(default=None, description="Tag filters")
    min_priority: Optional[int] = Field(default=None, description="Minimum priority threshold")


class SelectionResponse(BaseModel):
    """Response model for selection result."""
    server_name: str
    model_name: str
    capability_type: str
    key: str
    mode_used: str
    candidates_count: int
    selection_reason: str
    instance: Optional[dict] = None


@app.post("/api/v1/select/{capability_type}", response_model=SelectionResponse)
async def select_capability(
    capability_type: str,
    selection: SelectionRequest
):
    """
    Select server:model for a capability.

    Uses the unified selection system to find the best server:model
    combination based on selection configuration.

    Args:
        capability_type: Capability type (e.g., "text2image", "chat_completion")
        selection: Selection configuration

    Returns:
        SelectionResult with selected server_name, model_name, and metadata
    """
    try:
        from server.api.types import Capability, SelectionConfig, SelectionMode
        from server.service.ability_selection_service import SelectionError

        # Parse capability type
        try:
            capability = Capability(capability_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability type: {capability_type}"
            )

        # Build selection config
        try:
            mode = SelectionMode(selection.mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid selection mode: {selection.mode}. Valid modes: auto, server_only, exact"
            )

        config = SelectionConfig(
            mode=mode,
            server=selection.server,
            model=selection.model,
            tags=selection.tags,
            min_priority=selection.min_priority,
        )

        # Execute selection
        result = filmeto_api.selection_service.select(capability, config)

        return SelectionResponse(
            server_name=result.server_name,
            model_name=result.model_name,
            capability_type=result.capability_type.value,
            key=result.key,
            mode_used=result.mode_used.value,
            candidates_count=result.candidates_count,
            selection_reason=result.selection_reason,
            instance=result.instance.to_dict() if result.instance else None,
        )

    except HTTPException:
        raise
    except SelectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/select/{capability_type}/default", response_model=SelectionResponse)
async def get_default_capability(
    capability_type: str,
    tags: Optional[str] = None
):
    """
    Get default (highest priority) server:model for a capability.

    Convenience endpoint that returns the best available instance
    without requiring a full selection configuration.

    Args:
        capability_type: Capability type (e.g., "text2image")
        tags: Optional comma-separated tag filters

    Returns:
        SelectionResult with default server_name, model_name
    """
    try:
        from server.api.types import Capability

        # Parse capability type
        try:
            capability = Capability(capability_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability type: {capability_type}"
            )

        # Parse tags
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Get default instance
        result = filmeto_api.selection_service.get_default_instance(capability, tag_list)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No available instances for capability '{capability_type}'"
            )

        return SelectionResponse(
            server_name=result.server_name,
            model_name=result.model_name,
            capability_type=result.capability_type.value,
            key=result.key,
            mode_used="auto",
            candidates_count=1,
            selection_reason="Default (highest priority) selection",
            instance=result.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/select/{capability_type}/candidates")
async def list_selection_candidates(
    capability_type: str,
    tags: Optional[str] = None,
    min_priority: Optional[int] = None
):
    """
    List all candidate instances for selection.

    Returns all available instances for a capability, sorted by priority.

    Args:
        capability_type: Capability type (e.g., "text2image")
        tags: Optional comma-separated tag filters
        min_priority: Optional minimum priority filter

    Returns:
        List of candidate CapabilityInstance objects
    """
    try:
        from server.api.types import Capability

        # Parse capability type
        try:
            capability = Capability(capability_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability type: {capability_type}"
            )

        # Parse tags
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Get all instances
        instances = filmeto_api.selection_service.get_all_instances(
            capability,
            tags=tag_list,
            min_priority=min_priority
        )

        return {
            "capability_type": capability_type,
            "candidates": [inst.to_dict() for inst in instances],
            "total": len(instances),
            "filters": {
                "tags": tag_list,
                "min_priority": min_priority,
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest):
    """
    Create and enqueue a task for background execution.

    The task is validated and enqueued immediately. Use
    GET /api/v1/tasks/{task_id} to poll for progress and results.

    Args:
        task_request: Task creation request

    Returns:
        Task response with task_id
    """
    try:
        task = FilmetoTask(
            capability=Capability(task_request.capability),
            server_name=task_request.server_name,
            parameters=task_request.parameters,
            resources=[ResourceInput.from_dict(r) for r in task_request.resources],
            timeout=task_request.timeout,
            metadata=task_request.metadata
        )

        task_id = await filmeto_api.enqueue_task(task)

        return TaskResponse(
            task_id=task_id,
            status="queued",
            message="Task enqueued. Poll GET /api/v1/tasks/{task_id} for status."
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
    """
    try:
        # Convert request to FilmetoTask
        task = FilmetoTask(
            capability=Capability(task_request.capability),
            server_name=task_request.server_name,
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
            except ServerNotFoundError as e:
                error_data = {
                    "_type": "error",
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            except ServerExecutionError as e:
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


@app.get("/api/v1/queue/status")
async def queue_status():
    """
    Get current task queue and concurrency status.

    Returns:
        Queue info including active/queued counts and capacity
    """
    return filmeto_api.get_queue_info()


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


# ---------------------------------------------------------------------------
# OpenAI-compatible Chat Completion endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.

    Supports both streaming (``stream: true``) and non-streaming modes.
    Requests are routed to the appropriate LLM backend based on the model
    name and server configuration.
    """
    try:
        if request.stream:
            async def stream_generator():
                try:
                    async for chunk in filmeto_api.chat_completion_stream(request):
                        yield f"data: {chunk.model_dump_json()}\n\n"
                    yield "data: [DONE]\n\n"
                except ValueError as e:
                    error_data = json.dumps({
                        "error": {"message": str(e), "type": "invalid_request_error"}
                    })
                    yield f"data: {error_data}\n\n"
                except Exception as e:
                    error_data = json.dumps({
                        "error": {"message": str(e), "type": "server_error"}
                    })
                    yield f"data: {error_data}\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            response = await filmeto_api.chat_completion(request)
            return response.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models", response_model=ModelListResponse)
async def list_chat_models():
    """
    OpenAI-compatible model listing endpoint.

    Returns all models advertised by chat-capable servers.
    """
    try:
        models = filmeto_api.list_chat_models()
        return ModelListResponse(data=models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0", port=8000)