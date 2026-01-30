"""
ComfyUI Server Plugin

A plugin that integrates ComfyUI for AI image and video generation.
Supports multiple tools via configurable workflows.
"""

import os
import sys
import json
import random
import tempfile
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional, Tuple

# Import base plugin directly using file path to avoid naming conflicts
import importlib.util

# Get the absolute path to the base_plugin.py file
# Using __file__ to get the absolute path of this file, then navigate to the plugins directory
current_file_path = Path(__file__).resolve()  # Absolute path to this file
plugin_dir = current_file_path.parent  # Current plugin directory
plugins_dir = plugin_dir.parent  # Parent plugins directory (where base_plugin.py is)
base_plugin_path = plugins_dir / "base_plugin.py"  # Path to base_plugin.py

# Load the base plugin module directly
spec = importlib.util.spec_from_file_location("base_plugin", str(base_plugin_path))
base_plugin_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_plugin_module)

# Import the required classes
BaseServerPlugin = base_plugin_module.BaseServerPlugin
ToolConfig = base_plugin_module.ToolConfig

# Import the ComfyUI client using relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comfy_ui_client import ComfyUIClient

class ComfyUiServerPlugin(BaseServerPlugin):
    """
    Plugin for ComfyUI integration.
    """

    def __init__(self):
        super().__init__()
        # Use temporary directory for output files instead of plugin directory
        # Files will be copied to project resources directory after generation
        self.builtin_workflows_dir = Path(__file__).parent / "workflows"
        # Workspace workflows directory (will be set when workspace_path is available)
        self.workspace_workflows_dir = None

    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin metadata"""
        return {
            "name": "ComfyUI",
            "version": "1.3.0",
            "description": "ComfyUI integration for AI image and video generation",
            "author": "Filmeto Team",
            "engine": "comfyui"
        }

    def get_supported_tools(self) -> List[ToolConfig]:
        """Get list of tools supported by this plugin with their configs"""
        text2image_params = [
            {"name": "prompt", "type": "string", "required": True, "description": "Text prompt for generation"},
            {"name": "width", "type": "integer", "required": False, "default": 720, "description": "Image width"},
            {"name": "height", "type": "integer", "required": False, "default": 1280, "description": "Image height"}
        ]
        
        image2image_params = [
            {"name": "prompt", "type": "string", "required": True, "description": "Text prompt for transformation"},
            {"name": "input_image_path", "type": "string", "required": True, "description": "Path to input image"}
        ]
        
        image2video_params = [
            {"name": "prompt", "type": "string", "required": True, "description": "Text prompt for animation"},
            {"name": "input_image_path", "type": "string", "required": True, "description": "Path to input image"}
        ]

        return [
            ToolConfig(name="text2image", description="Generate image from text prompt using ComfyUI", parameters=text2image_params),
            ToolConfig(name="image2image", description="Transform image using ComfyUI", parameters=image2image_params),
            ToolConfig(name="image2video", description="Animate image using ComfyUI", parameters=image2video_params),
        ]

    def init_ui(self, workspace_path: str, server_config: Optional[Dict[str, Any]] = None):
        """
        Initialize custom UI widget for server configuration.

        Args:
            workspace_path: Path to workspace directory
            server_config: Optional existing server configuration

        Returns:
            QWidget: Custom configuration widget
        """
        try:
            # Import the ComfyUI config widget
            from server.plugins.comfy_ui_server.config.comfy_ui_config_widget import ComfyUIConfigWidget

            # Create and return the widget using the plugin info and config
            widget = ComfyUIConfigWidget(workspace_path, server_config, None)
            return widget
        except Exception as e:
            logger.error(f"Failed to create ComfyUI config widget: {e}", exc_info=True)
            return None

    async def execute_task(
        self,
        task_data: Dict[str, Any],
        progress_callback: Callable[[float, str, Dict[str, Any]], None]
    ) -> Dict[str, Any]:
        """
        Execute a task based on its tool type.
        """
        task_id = task_data.get("task_id", "unknown")
        tool_name = task_data.get("tool_name", "")
        parameters = task_data.get("parameters", {})
        metadata = task_data.get("metadata", {})
        server_config = metadata.get("server_config", {})
        
        # Extract workspace_path and server_name from metadata for workflow loading
        # These are set by ServerManager when executing tasks
        workspace_path = metadata.get("workspace_path")
        server_name = metadata.get("server_name")

        # ComfyUI server details
        server_url = server_config.get("server_url", "http://localhost")
        port = server_config.get("port", 8188)
        base_url = f"{server_url}:{port}"
        
        if not base_url.startswith("http"):
            base_url = "http://" + base_url

        client = ComfyUIClient(base_url)
        
        # Prepare server config for workflow loading (include workspace_path and server_name)
        workflow_server_config = {
            "workspace_path": metadata.get("workspace_path"),
            "server_name": metadata.get("server_name")
        }

        try:
            if tool_name == "text2image":
                return await self._execute_text2image(client, task_id, parameters, progress_callback, workflow_server_config)
            elif tool_name == "image2image":
                return await self._execute_image2image(client, task_id, parameters, progress_callback, workflow_server_config)
            elif tool_name == "image2video":
                return await self._execute_image2video(client, task_id, parameters, progress_callback, workflow_server_config)
            else:
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error_message": f"Unsupported tool: {tool_name}",
                    "output_files": []
                }

        except Exception as e:
            logger.error(f"Error executing task with tool {tool_name}: {e}", exc_info=True)
            return {
                "task_id": task_id,
                "status": "error",
                "error_message": str(e),
                "output_files": []
            }

    def _get_workspace_workflows_dir(self, server_config: Dict[str, Any]) -> Optional[Path]:
        """
        Get workspace workflows directory from server config.
        
        Args:
            server_config: Server configuration containing workspace_path and server name
            
        Returns:
            Path to workspace workflows directory or None
        """
        workspace_path = server_config.get("workspace_path")
        server_name = server_config.get("server_name")
        
        if workspace_path and server_name:
            workspace_workflows_dir = Path(workspace_path) / "servers" / server_name / "workflows"
            return workspace_workflows_dir if workspace_workflows_dir.exists() else None
        return None
    
    async def _load_workflow(self, name: str, server_config: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Load workflow JSON from workspace directory first, then fallback to builtin directory.
        
        Args:
            name: Workflow name (e.g., "text2image")
            server_config: Optional server configuration for workspace path
            
        Returns:
            tuple: (prompt_graph, filmeto_config)
            - prompt_graph: The ComfyUI workflow prompt graph
            - filmeto_config: Filmeto-specific configuration including node mappings
        """
        workflow_path = None
        
        # Try workspace directory first (if available)
        if server_config:
            workspace_workflows_dir = self._get_workspace_workflows_dir(server_config)
            if workspace_workflows_dir:
                workflow_path = workspace_workflows_dir / f"{name}.json"
                if not workflow_path.exists() and name == "text2image":
                    workflow_path = workspace_workflows_dir / "text2image_workflow.json"
        
        # Fallback to builtin directory
        if not workflow_path or not workflow_path.exists():
            workflow_path = self.builtin_workflows_dir / f"{name}.json"
            if not workflow_path.exists():
                # Fallback for text2image naming inconsistency
                if name == "text2image":
                    workflow_path = self.builtin_workflows_dir / "text2image_workflow.json"
        
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {name}.json (checked workspace and builtin directories)")
            
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # Extract filmeto configuration (if exists)
        filmeto_config = workflow.get("filmeto", {})
        
        # Extract prompt graph (ComfyUI workflow)
        prompt_graph = workflow.get("prompt", workflow)
        
        # If prompt_graph is the whole workflow (old format), extract just the prompt
        if "prompt" in prompt_graph and isinstance(prompt_graph["prompt"], dict):
            prompt_graph = prompt_graph["prompt"]
        
        return prompt_graph, filmeto_config

    def _apply_node_value(self, prompt_graph: Dict[str, Any], node_id: str, input_key: str, value: Any) -> bool:
        """
        Apply a value to a specific node input in the prompt graph.
        
        Args:
            prompt_graph: The ComfyUI workflow prompt graph
            node_id: Node ID to update
            input_key: Input key within the node's inputs
            value: Value to set
            
        Returns:
            bool: True if the value was applied, False if node doesn't exist
        """
        if node_id and node_id in prompt_graph:
            if "inputs" not in prompt_graph[node_id]:
                prompt_graph[node_id]["inputs"] = {}
            prompt_graph[node_id]["inputs"][input_key] = value
            return True
        return False

    def _apply_seed_node(self, prompt_graph: Dict[str, Any], node_id: str) -> bool:
        """
        Apply random seed to a seed node.
        
        Args:
            prompt_graph: The ComfyUI workflow prompt graph
            node_id: Seed node ID to update
            
        Returns:
            bool: True if the seed was applied, False if node doesn't exist
        """
        if not node_id or node_id not in prompt_graph:
            return False
        
        # Generate random seed (using large integer range similar to ComfyUI)
        random_seed = random.randint(0, 2**32 - 1)
        
        # Try to set seed in inputs
        if "inputs" not in prompt_graph[node_id]:
            prompt_graph[node_id]["inputs"] = {}
        
        # Set seed value
        prompt_graph[node_id]["inputs"]["seed"] = random_seed
        return True

    def _apply_input_nodes(self, prompt_graph: Dict[str, Any], input_nodes: Any, values: Any, input_key: str = "image") -> int:
        """
        Apply values to multiple input nodes in the prompt graph.
        Supports mapping multiple input images to multiple nodes (e.g., start frame and end frame).
        
        Args:
            prompt_graph: The ComfyUI workflow prompt graph
            input_nodes: Node ID(s) to update - can be:
                - Single node ID (string): applies first value to this node
                - List of node IDs: maps values to nodes in order
            values: Value(s) to set - can be:
                - Single value: applies to all nodes (if single node) or first node (if multiple nodes)
                - List of values: maps to nodes in order
            input_key: Input key within the node's inputs (default: "image")
            
        Returns:
            int: Number of nodes successfully updated
        """
        if not input_nodes:
            return 0
        
        # Handle both single node ID (string) and list of node IDs
        if isinstance(input_nodes, str):
            input_nodes = [input_nodes]
        
        # Handle both single value and list of values
        if not isinstance(values, list):
            values = [values]
        
        count = 0
        for idx, node_id in enumerate(input_nodes):
            # Use corresponding value if available, otherwise use first value
            value = values[idx] if idx < len(values) else values[0]
            if self._apply_node_value(prompt_graph, node_id, input_key, value):
                count += 1
        
        return count

    async def _execute_text2image(self, client, task_id, parameters, progress_callback, server_config: Optional[Dict[str, Any]] = None):
        prompt_text = parameters.get("prompt", "")
        width = parameters.get("width", 720)
        height = parameters.get("height", 1280)
        
        progress_callback(5, "Loading workflow...", {})
        prompt_graph, filmeto_config = await self._load_workflow("text2image", server_config)
        
        # Get node mappings from filmeto config
        node_mapping = filmeto_config.get("node_mapping", {})
        
        # Apply prompt to prompt node (if configured)
        prompt_node = node_mapping.get("prompt_node")
        if prompt_node:
            self._apply_node_value(prompt_graph, prompt_node, "text", prompt_text)
        
        # Apply width/height if nodes are specified
        width_node = node_mapping.get("width_node")
        if width_node:
            self._apply_node_value(prompt_graph, width_node, "width", width)
            
        height_node = node_mapping.get("height_node")
        if height_node:
            self._apply_node_value(prompt_graph, height_node, "height", height)
        
        # Apply random seed to seed node (if configured)
        seed_node = node_mapping.get("seed_node")
        if seed_node:
            self._apply_seed_node(prompt_graph, seed_node)
        
        # Create temporary directory for this task's output files
        output_dir = Path(tempfile.mkdtemp(prefix=f"comfyui_{task_id}_"))
            
        files = await client.run_workflow(prompt_graph, progress_callback, output_dir, task_id)
        return {"task_id": task_id, "status": "success", "output_files": files}

    async def _execute_image2image(self, client, task_id, parameters, progress_callback, server_config: Optional[Dict[str, Any]] = None):
        prompt_text = parameters.get("prompt", "")
        input_image_path = parameters.get("input_image_path")
        
        # Check metadata for processed resources (preferred)
        processed_resources = parameters.get("processed_resources")
        if processed_resources:
            input_image_paths = processed_resources
        else:
            input_image_paths = [input_image_path] if input_image_path else []

        progress_callback(5, "Uploading image(s)...", {})
        comfy_filenames = []
        for img_path in input_image_paths:
            comfy_filename = await client.upload_image(img_path)
            if not comfy_filename:
                raise Exception(f"Failed to upload image to ComfyUI: {img_path}")
            comfy_filenames.append(comfy_filename)
            
        progress_callback(8, "Loading workflow...", {})
        prompt_graph, filmeto_config = await self._load_workflow("image2image", server_config)
        
        # Get node mappings from filmeto config
        node_mapping = filmeto_config.get("node_mapping", {})
        
        # Apply input image(s) to input node(s) - support multiple input nodes and multiple images
        input_node = node_mapping.get("input_node")
        if input_node and comfy_filenames:
            self._apply_input_nodes(prompt_graph, input_node, comfy_filenames, "image")
        
        # Apply prompt to prompt node (if configured)
        prompt_node = node_mapping.get("prompt_node")
        if prompt_node:
            self._apply_node_value(prompt_graph, prompt_node, "text", prompt_text)
        
        # Apply random seed to seed node (if configured)
        seed_node = node_mapping.get("seed_node")
        if seed_node:
            self._apply_seed_node(prompt_graph, seed_node)
        
        # Create temporary directory for this task's output files
        output_dir = Path(tempfile.mkdtemp(prefix=f"comfyui_{task_id}_"))
        
        files = await client.run_workflow(prompt_graph, progress_callback, output_dir, task_id)
        return {"task_id": task_id, "status": "success", "output_files": files}

    async def _execute_image2video(self, client, task_id, parameters, progress_callback, server_config: Optional[Dict[str, Any]] = None):
        prompt_text = parameters.get("prompt", "")
        input_image_path = parameters.get("input_image_path")
        
        # Check metadata for processed resources (preferred) - supports multiple images (e.g., start frame, end frame)
        processed_resources = parameters.get("processed_resources")
        if processed_resources:
            input_image_paths = processed_resources
        else:
            input_image_paths = [input_image_path] if input_image_path else []

        progress_callback(5, "Uploading image(s)...", {})
        comfy_filenames = []
        for img_path in input_image_paths:
            comfy_filename = await client.upload_image(img_path)
            if not comfy_filename:
                raise Exception(f"Failed to upload image to ComfyUI: {img_path}")
            comfy_filenames.append(comfy_filename)
            
        progress_callback(8, "Loading workflow...", {})
        prompt_graph, filmeto_config = await self._load_workflow("image2video", server_config)
        
        # Get node mappings from filmeto config
        node_mapping = filmeto_config.get("node_mapping", {})
        
        # Apply input image(s) to input node(s) - support multiple input nodes and multiple images
        # Example: ["start_frame_node", "end_frame_node"] with [start_image, end_image]
        input_node = node_mapping.get("input_node")
        if input_node and comfy_filenames:
            self._apply_input_nodes(prompt_graph, input_node, comfy_filenames, "image")
        
        # Apply prompt to prompt node (if configured)
        prompt_node = node_mapping.get("prompt_node")
        if prompt_node:
            prompt_input_key = node_mapping.get("prompt_input_key", "text")
            # Try to apply with specified key first
            if not self._apply_node_value(prompt_graph, prompt_node, prompt_input_key, prompt_text):
                # If node exists but key doesn't, try common prompt input keys
                if prompt_node in prompt_graph:
                    node_inputs = prompt_graph[prompt_node].get("inputs", {})
                    for key in ["text", "positive_prompt", "prompt"]:
                        if key in node_inputs:
                            node_inputs[key] = prompt_text
                            break
        
        # Apply random seed to seed node (if configured)
        seed_node = node_mapping.get("seed_node")
        if seed_node:
            self._apply_seed_node(prompt_graph, seed_node)
        
        # Create temporary directory for this task's output files
        output_dir = Path(tempfile.mkdtemp(prefix=f"comfyui_{task_id}_"))
        
        files = await client.run_workflow(prompt_graph, progress_callback, output_dir, task_id)
        return {"task_id": task_id, "status": "success", "output_files": files}

if __name__ == "__main__":
    plugin = ComfyUiServerPlugin()
    plugin.run()
