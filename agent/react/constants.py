"""Constants for ReAct pattern."""
from enum import Enum


class StopReason(str, Enum):
    """Stop reason constants for ReAct actions."""
    FINAL_ACTION = "final_action"
    MAX_STEPS = "max_steps_reached"
    NO_JSON = "no_json_payload"
    UNKNOWN_TYPE = "unknown_action_type"
    USER_INTERRUPTED = "user_interrupted"
    LLM_ERROR = "llm_error"
    TOOL_ERROR = "tool_error"


class ReactConfig:
    """Default configuration values for React."""
    DEFAULT_MAX_STEPS = 100
    DEFAULT_MAX_INSTANCES = 100
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes
