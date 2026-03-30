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
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from server.api.filmeto_api import FilmetoApi
from server.api.types import (
    FilmetoTask, TaskProgress, TaskResult, Ability, ResourceInput,
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
    model_config = ConfigDict(populate_by_name=True)

    ability: str = Field(
        ...,
        description="Ability to use (e.g., 'text2image')",
        validation_alias=AliasChoices("ability", "capability"),
    )
    server_name: str = Field(..., description="Server name to execute")
    parameters: dict = Field(..., description="Ability-specific parameters")
    resources: list = Field(default_factory=list, description="Input resources")
    timeout: int = Field(default=300, description="Timeout in seconds")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class TaskResponse(BaseModel):
    """Response model for task creation"""
    task_id: str
    status: str
    message: str


class AbilitySummary(BaseModel):
    """Ability information"""
    name: str
    display_name: str


class ServerInfo(BaseModel):
    """Server information"""
    name: str
    version: str
    description: str
    ability_type: str
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


@app.get("/api/v1/abilities")
async def list_abilities(ability_type: Optional[str] = None):
    """
    List all ability instances (server:model). Optional filter by ability type.

    Example:
        GET /api/v1/abilities?ability_type=text2image
    """
    try:
        items = filmeto_api.list_abilities(ability_type)
        return {
            "abilities": items,
            "total": len(items),
            "ability_type_filter": ability_type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/abilities/groups")
async def list_ability_groups():
    """List abilities grouped by ability type."""
    try:
        groups = filmeto_api.get_ability_groups()
        return {"groups": groups, "total_groups": len(groups)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/abilities/{key}")
async def get_ability_instance_http(key: str):
    """Get one ability instance by ``server:model`` key."""
    try:
        inst = filmeto_api.get_ability_instance(key)
        if not inst:
            raise HTTPException(
                status_code=404,
                detail=f"Ability instance '{key}' not found",
            )
        return inst
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/abilities/select/{ability_type}")
async def get_ability_selection_context_http(
    ability_type: str,
    user_requirement: Optional[str] = None,
):
    """LLM-oriented context for choosing a server:model for an ability."""
    try:
        return filmeto_api.get_ability_selection_context(
            ability_type,
            user_requirement or "",
        )
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
    ability_type: str
    key: str
    mode_used: str
    candidates_count: int
    selection_reason: str
    instance: Optional[dict] = None


@app.post("/api/v1/select/{ability_type}", response_model=SelectionResponse)
async def select_ability(ability_type: str, selection: SelectionRequest):
    """Select server:model for an ability."""
    try:
        from server.api.types import Ability, SelectionConfig, SelectionMode
        from server.service.ability_selection_service import SelectionError

        try:
            ability = Ability(ability_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ability type: {ability_type}",
            )

        try:
            mode = SelectionMode(selection.mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid selection mode: {selection.mode}. "
                    "Valid modes: auto, server_only, exact"
                ),
            )

        config = SelectionConfig(
            mode=mode,
            server=selection.server,
            model=selection.model,
            tags=selection.tags,
            min_priority=selection.min_priority,
        )

        result = filmeto_api.selection_service.select(ability, config)

        return SelectionResponse(
            server_name=result.server_name,
            model_name=result.model_name,
            ability_type=result.ability_type.value,
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


@app.get("/api/v1/select/{ability_type}/default", response_model=SelectionResponse)
async def get_default_ability(ability_type: str, tags: Optional[str] = None):
    """Default (highest priority) server:model for an ability."""
    try:
        from server.api.types import Ability

        try:
            ability = Ability(ability_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ability type: {ability_type}",
            )

        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        result = filmeto_api.selection_service.get_default_instance(ability, tag_list)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No available instances for ability '{ability_type}'",
            )

        return SelectionResponse(
            server_name=result.server_name,
            model_name=result.model_name,
            ability_type=result.ability_type.value,
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


@app.get("/api/v1/select/{ability_type}/candidates")
async def list_ability_selection_candidates(
    ability_type: str,
    tags: Optional[str] = None,
    min_priority: Optional[int] = None,
):
    """List candidate server:model instances for an ability."""
    try:
        from server.api.types import Ability

        try:
            ability = Ability(ability_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ability type: {ability_type}",
            )

        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        instances = filmeto_api.selection_service.get_all_instances(
            ability,
            tags=tag_list,
            min_priority=min_priority,
        )

        return {
            "ability_type": ability_type,
            "candidates": [inst.to_dict() for inst in instances],
            "total": len(instances),
            "filters": {
                "tags": tag_list,
                "min_priority": min_priority,
            },
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
            ability=Ability(task_request.ability),
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
            ability=Ability(task_request.ability),
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