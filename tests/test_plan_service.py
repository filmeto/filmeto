"""
Test script for the Plan Service functionality
"""
import sys
import os
import warnings

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.plan.plan_service import PlanService
from agent.plan.plan_models import PlanTask, PlanStatus, TaskStatus


def test_create_plan():
    """Test creating a plan using PlanService.get_instance()"""
    print("Testing plan creation...")

    # Create PlanService instance using get_instance
    plan_service = PlanService.get_instance(None, "TestProject")

    # Create PlanTask objects
    tasks = [
        PlanTask(
            id='task_1',
            name='Research',
            description='Research the problem',
            title='researcher',
            parameters={'param1': 'value1'},
            needs=[]
        ),
        PlanTask(
            id='task_2',
            name='Analysis',
            description='Analyze the findings',
            title='analyst',
            parameters={'param2': 'value2'},
            needs=['task_1']
        ),
        PlanTask(
            id='task_3',
            name='Report',
            description='Write a report',
            title='writer',
            parameters={'param3': 'value3'},
            needs=['task_2']
        )
    ]

    plan = plan_service.create_plan(
        project_name='TestProject',
        name='Test Plan',
        description='A test plan for verifying plan service functionality',
        tasks=tasks
    )

    print(f"Created plan with ID: {plan.id}")
    print(f"Plan name: {plan.name}")
    print(f"Number of tasks: {len(plan.tasks)}")

    for task in plan.tasks:
        print(f"  - Task: {task.name} (ID: {task.id}) - Needs: {task.needs}")

    return plan


def test_plan_execution():
    """Test plan execution flow using PlanService.get_instance()"""
    print("\nTesting plan execution flow...")

    # Create PlanService instance using get_instance
    plan_service = PlanService.get_instance(None, "TestProject")

    # Create PlanTask objects
    tasks = [
        PlanTask(
            id='task_1',
            name='Research',
            description='Research the problem',
            title='researcher',
            parameters={'param1': 'value1'},
            needs=[]
        ),
        PlanTask(
            id='task_2',
            name='Analysis',
            description='Analyze the findings',
            title='analyst',
            parameters={'param2': 'value2'},
            needs=['task_1']
        ),
        PlanTask(
            id='task_3',
            name='Report',
            description='Write a report',
            title='writer',
            parameters={'param3': 'value3'},
            needs=['task_2']
        )
    ]

    # Create plan
    plan = plan_service.create_plan(
        project_name='TestProject',
        name='Test Execution Plan',
        description='A test plan for verifying plan execution functionality',
        tasks=tasks
    )

    # Create plan instance
    plan_instance = plan_service.create_plan_instance(plan)
    print(f"Created plan instance with ID: {plan_instance.instance_id}")

    # Start execution
    started = plan_service.start_plan_execution(plan_instance)
    print(f"Started plan execution: {started}")

    # Get ready tasks
    ready_tasks = plan_service.get_next_ready_tasks(plan_instance)
    print(f"Ready tasks: {len(ready_tasks)}")

    # Simulate marking tasks as completed
    for task in ready_tasks:
        plan_service.mark_task_running(plan_instance, task.id)
        print(f"Task {task.name} is now running")
        plan_service.mark_task_completed(plan_instance, task.id)
        print(f"Task {task.name} completed")

    # Get next ready tasks (should be task_2)
    ready_tasks = plan_service.get_next_ready_tasks(plan_instance)
    print(f"Ready tasks after task_1 completion: {len(ready_tasks)}")

    print(f"Plan status: {plan_instance.status.value}")
    print(f"Instance ID: {plan_instance.instance_id}")

    for task in plan_instance.tasks:
        print(f"  - Task: {task.name} - Status: {task.status.value}")

    return plan, plan_instance


def test_plan_service_class():
    """Test using PlanService.get_instance()"""
    print("\nTesting PlanService.get_instance()...")

    # Create PlanService instance using get_instance
    plan_service = PlanService.get_instance(None, "TestProject")

    # Verify instance caching - calling again should return the same instance
    plan_service2 = PlanService.get_instance(None, "TestProject")
    assert plan_service is plan_service2, "get_instance should return the same instance for the same workspace/project"
    print("✓ Instance caching works correctly")

    # Create PlanTask objects
    task_dicts = [
        PlanTask(
            id='direct_task_1',
            name='Direct Task 1',
            description='A task created directly through PlanService',
            title='executor',
            parameters={'step': 1},
            needs=[]
        ),
        PlanTask(
            id='direct_task_2',
            name='Direct Task 2',
            description='Another task created directly through PlanService',
            title='executor',
            parameters={'step': 2},
            needs=['direct_task_1']
        )
    ]

    # Create a plan using the service
    plan = plan_service.create_plan(
        project_name='TestProject',
        name='Direct Test Plan',
        description='A test plan created directly through PlanService',
        tasks=task_dicts
    )

    print(f"Created plan with ID: {plan.id}")
    print(f"Plan name: {plan.name}")
    print(f"Number of tasks: {len(plan.tasks)}")

    # Create an instance of the plan
    plan_instance = plan_service.create_plan_instance(plan)
    print(f"Created plan instance with ID: {plan_instance.instance_id}")

    # Start execution
    started = plan_service.start_plan_execution(plan_instance)
    print(f"Started plan execution: {started}")

    # Get ready tasks
    ready_tasks = plan_service.get_next_ready_tasks(plan_instance)
    print(f"Ready tasks: {len(ready_tasks)}")

    # Test instance management
    print("\nTesting instance management...")
    print(f"Current instances: {PlanService.list_instances()}")
    assert PlanService.has_instance(None, "TestProject"), "Should have instance for TestProject"
    print("✓ has_instance works correctly")

    removed = PlanService.remove_instance(None, "TestProject")
    assert removed, "Should successfully remove instance"
    print("✓ remove_instance works correctly")
    assert not PlanService.has_instance(None, "TestProject"), "Instance should be removed"
    print("✓ Instance successfully removed")

    return plan, plan_instance


if __name__ == "__main__":
    print("Running Plan Service tests...\n")

    # Test 1: Create a plan
    plan = test_create_plan()

    # Test 2: Execute a plan
    plan, plan_instance = test_plan_execution()

    # Test 3: Use PlanService.get_instance()
    plan, plan_instance = test_plan_service_class()

    # Clean up
    PlanService.clear_all_instances()
    print("\n✓ Cleared all instances")

    print("\nAll tests completed successfully!")
