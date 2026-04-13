"""
React Service Module

Manages React instances by project name and react type.
"""
from collections import OrderedDict
from threading import Lock
from typing import Any, Callable, Dict, List, Optional
import logging

from .react import React
from .constants import ReactConfig

logger = logging.getLogger(__name__)


class ReactService:
    """
    Singleton service to manage React instances with reuse capability and LRU eviction.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ReactService, cls).__new__(cls)
        return cls._instance

    def __init__(self, max_instances: int = 100):
        with self._lock:
            if hasattr(self, '_initialized') and self._initialized:
                return
            self._instances: OrderedDict[str, React] = OrderedDict()
            self._max_instances = max_instances
            self._initialized = True
            logger.debug(f"ReactService initialized with max_instances={max_instances}")

    def _generate_instance_key(self, project_name: str, react_type: str) -> str:
        return f"{project_name}:{react_type}"

    def _evict_if_needed(self) -> None:
        """Evict oldest instance if limit exceeded."""
        if len(self._instances) > self._max_instances:
            oldest_key = next(iter(self._instances))
            del self._instances[oldest_key]
            logger.debug(f"Evicted oldest React instance: {oldest_key}")

    def _access_instance(self, key: str) -> None:
        """Move instance to end of OrderedDict (mark as recently used)."""
        if key in self._instances:
            self._instances.move_to_end(key)

    def get_or_create_react(
        self,
        project_name: str,
        react_type: str,
        build_prompt_function: Callable[[str], str],
        available_tool_names: Optional[List[str]] = None,
        *,
        workspace=None,
        chat_service=None,
        max_steps: int = ReactConfig.DEFAULT_MAX_STEPS,
    ) -> React:
        instance_key = self._generate_instance_key(project_name, react_type)

        with self._lock:
            if instance_key in self._instances:
                self._access_instance(instance_key)
                return self._instances[instance_key]

            self._evict_if_needed()

            react_instance = React(
                workspace=workspace,
                project_name=project_name,
                react_type=react_type,
                build_prompt_function=build_prompt_function,
                available_tool_names=available_tool_names,
                chat_service=chat_service,
                max_steps=max_steps,
            )

            self._instances[instance_key] = react_instance
            logger.debug(f"Created new React instance: {instance_key}")
            return react_instance

    def get_react(self, project_name: str, react_type: str) -> Optional[React]:
        instance_key = self._generate_instance_key(project_name, react_type)
        with self._lock:
            if instance_key in self._instances:
                self._access_instance(instance_key)
                return self._instances[instance_key]
            return None

    def remove_react(self, project_name: str, react_type: str) -> bool:
        instance_key = self._generate_instance_key(project_name, react_type)
        with self._lock:
            if instance_key in self._instances:
                del self._instances[instance_key]
                logger.debug(f"Removed React instance: {instance_key}")
                return True
            return False

    def clear_all_instances(self) -> None:
        with self._lock:
            count = len(self._instances)
            self._instances.clear()
            logger.debug(f"Cleared {count} React instances")

    def list_instances(self) -> Dict[str, React]:
        with self._lock:
            return self._instances.copy()

    def get_instance_count(self) -> int:
        with self._lock:
            return len(self._instances)

    def get_metrics(self) -> Dict[str, Any]:
        """Get service-wide metrics."""
        with self._lock:
            instance_metrics = {}
            for key, instance in self._instances.items():
                instance_metrics[key] = instance.get_metrics()
            return {
                "total_instances": len(self._instances),
                "max_instances": self._max_instances,
                "instances": instance_metrics,
            }


react_service = ReactService()
