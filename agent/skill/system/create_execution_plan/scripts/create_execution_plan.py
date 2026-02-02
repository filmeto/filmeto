#!/usr/bin/env python3
"""
Execution Plan Creation Skill Script

This script creates execution plans for film production projects using the create_plan tool.
"""
import json
import sys
import argparse
import logging
from typing import Dict, Any, TYPE_CHECKING
import os
import ast

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent.tool.tool_context import ToolContext


def execute(context: 'ToolContext', args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the create_execution_plan skill in context.

    This is the main entry point for in-context execution via SkillExecutor.
    It calls the 'create_plan' tool using the execute_tool function.

    Args:
        context: SkillContext object containing workspace and project
        args: Dictionary of arguments for the skill

    Returns:
        dict: Result of the operation with success status and message
    """
    try:
        # Extract arguments
        plan_name = args.get('plan_name')
        description = args.get('description', '')
        tasks = args.get('tasks', [])

        if not plan_name:
            return {
                "success": False,
                "message": "plan_name is required"
            }

        # Call the 'create_plan' tool using execute_tool
        # The parameters for the tool are passed in the parameters dict
        tool_params = {
            'title': plan_name,
            'description': description,
            'tasks': tasks
        }

        # Use execute_tool to call the create_plan tool
        result = execute_tool("create_plan", tool_params)

        # Process the result from the tool
        if result and isinstance(result, dict):
            if 'id' in result:  # If the tool returned a plan ID, it was successful
                return {
                    "success": True,
                    "message": f"Execution plan '{plan_name}' created successfully",
                    "plan_id": result['id'],
                    "plan_name": result.get('title', plan_name),
                    "project": result.get('project', 'Unknown Project')
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to create execution plan '{plan_name}': {result.get('message', 'Unknown error')}"
                }
        else:
            return {
                "success": False,
                "message": f"Failed to create execution plan '{plan_name}': Unexpected result format"
            }

    except Exception as e:
        logger.error(f"Error creating execution plan: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error creating execution plan: {str(e)}"
        }


def create_execution_plan(plan_name: str, description: str = "", tasks: list = None) -> Dict[str, Any]:
    """
    Create an execution plan using the create_plan tool.

    Args:
        plan_name (str): Name of the execution plan
        description (str): Description of the plan
        tasks (list): Array of tasks for the plan

    Returns:
        dict: Result of the operation with success status and message
    """
    try:
        # Call the 'create_plan' tool using execute_tool
        # The parameters for the tool are passed in the parameters dict
        tool_params = {
            'title': plan_name,
            'description': description,
            'tasks': tasks or []
        }

        # Use execute_tool to call the create_plan tool
        result = execute_tool("create_plan", tool_params)

        # Process the result from the tool
        if result and isinstance(result, dict):
            if 'id' in result:  # If the tool returned a plan ID, it was successful
                return {
                    "success": True,
                    "message": f"Execution plan '{plan_name}' created successfully",
                    "plan_id": result['id'],
                    "plan_name": result.get('title', plan_name)
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to create execution plan '{plan_name}': {result.get('message', 'Unknown error')}"
                }
        else:
            return {
                "success": False,
                "message": f"Failed to create execution plan '{plan_name}': Unexpected result format"
            }

    except Exception as e:
        logger.error(f"Error creating execution plan: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error creating execution plan: {str(e)}"
        }


def main():
    """CLI entry point for standalone execution."""
    # Handle both traditional positional args and new approach with named args
    args = sys.argv[1:]  # Skip script name

    plan_name = None
    description = ""
    tasks_str = "[]"
    project_path = None

    # Process arguments by looking for known flags first
    i = 0
    while i < len(args):
        if args[i] == '--plan-name' and i + 1 < len(args):
            plan_name = args[i + 1]
            i += 2
        elif args[i] == '--description' and i + 1 < len(args):
            description = args[i + 1]
            i += 2
        elif args[i] == '--tasks' and i + 1 < len(args):
            tasks_str = args[i + 1]
            i += 2
        elif args[i] == '--project-path' and i + 1 < len(args):
            project_path = args[i + 1]
            i += 2
        else:
            # This is either a positional argument or an unknown flag
            # For backward compatibility, assume first non-flag argument is plan_name
            if plan_name is None and not args[i].startswith('--'):
                plan_name = args[i]
                i += 1
            # For the new approach, project_path might be passed as a positional argument
            elif project_path is None and not args[i].startswith('--'):
                project_path = args[i]
                i += 1
            else:
                # Skip unknown arguments
                i += 1

    # Validate required arguments
    if not plan_name:
        error_result = {
            "success": False,
            "error": "missing_plan_name",
            "message": "plan_name is required"
        }
        print(json.dumps(error_result, indent=2))

    if not project_path:
        error_result = {
            "success": False,
            "error": "missing_project_path",
            "message": "project_path is required"
        }
        print(json.dumps(error_result, indent=2))

    try:
        # Parse tasks - try JSON first, then fall back to Python literal evaluation
        try:
            tasks = json.loads(tasks_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to parse as Python literal
            try:
                tasks = ast.literal_eval(tasks_str)
            except (ValueError, SyntaxError):
                raise json.JSONDecodeError(f"Invalid JSON or Python literal for tasks: {tasks_str}", tasks_str, 0)

        # Create the execution plan
        result = create_execution_plan(plan_name, description, tasks)

        print(json.dumps(result, indent=2))

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON for tasks: {e}", exc_info=True)
        error_result = {
            "success": False,
            "error": "invalid_json",
            "message": f"Invalid JSON for tasks: {tasks_str}"
        }
        print(json.dumps(error_result, indent=2))
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Error in execution plan creation: {str(e)}"
        }
        print(json.dumps(error_result, indent=2))

# Alias for SkillExecutor compatibility
execute_in_context = execute


if __name__ == "__main__":
    main()