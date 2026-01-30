"""
Global signal manager for plan-related events.
"""

from PySide6.QtCore import QObject, Signal, QThread


class PlanSignalManager(QObject):
    """
    Global signal manager for plan-related events.
    This allows loose coupling between PlanService and UI components.
    """
    
    # Signal emitted when a plan is created
    plan_created = Signal(str, str)  # project_name, plan_id
    
    # Signal emitted when a plan is updated
    plan_updated = Signal(str, str)  # project_name, plan_id
    
    # Signal emitted when a plan instance is created
    plan_instance_created = Signal(str, str, str)  # project_name, plan_id, instance_id
    
    # Signal emitted when a plan instance status is updated
    plan_instance_status_updated = Signal(str, str, str)  # project_name, plan_id, instance_id
    
    # Signal emitted when a task status is updated
    task_status_updated = Signal(str, str, str, str)  # project_name, plan_id, instance_id, task_id
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of PlanSignalManager."""
        if cls._instance is None:
            # Ensure we're creating the instance in the main thread
            cls._instance = PlanSignalManager()
        return cls._instance


# Global instance for easy access
plan_signal_manager = PlanSignalManager.get_instance()