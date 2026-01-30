"""
Bailian Server Plugin

Integrates Alibaba Cloud Bailian (DashScope) AI services.
Supports text-to-image, image-to-image, and Bailian App tools.
"""

import os
import sys
import time
import asyncio
import json
import uuid
import requests
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional

# Add parent directory to path to import base_plugin
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.plugins.base_plugin import BaseServerPlugin, ToolConfig

# Try to import SDKs
try:
    import dashscope
    from dashscope import ImageSynthesis
except ImportError:
    print("Warning: dashscope SDK not found")

try:
    import broadscope_bailian
    from broadscope_bailian import Completions, AccessTokenClient
except ImportError:
    print("Warning: broadscope-bailian SDK not found")

class BailianServerPlugin(BaseServerPlugin):
    """
    Plugin for Alibaba Cloud Bailian integration.
    """

    def __init__(self):
        super().__init__()
        self.output_dir = Path(__file__).parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)

    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin metadata"""
        return {
            "name": "Bailian Server",
            "version": "1.2.0",
            "description": "Alibaba Cloud Bailian (DashScope & Broadscope) integration",
            "author": "Filmeto Team",
            "engine": "bailian"
        }

    def init_ui(self, workspace_path: str, server_config: Optional[Dict[str, Any]] = None):
        """
        Initialize custom UI widget for server configuration.
        """
        try:
            from server.plugins.bailian_server.config.bailian_config_widget import BailianConfigWidget
            return BailianConfigWidget(workspace_path, server_config)
        except Exception as e:
            print(f"Failed to create Bailian config widget: {e}")
            return None

    def get_supported_tools(self) -> List[ToolConfig]:
        """Get list of tools supported by this plugin with their configs"""
        text2image_params = [
            {"name": "prompt", "type": "string", "required": True, "description": "Text prompt for generation"},
            {"name": "model", "type": "string", "required": False, "default": "wanx-v1", "description": "Model to use (e.g., wanx-v1)"},
            {"name": "width", "type": "integer", "required": False, "default": 1024, "description": "Image width"},
            {"name": "height", "type": "integer", "required": False, "default": 1024, "description": "Image height"}
        ]
        
        image2image_params = [
            {"name": "prompt", "type": "string", "required": True, "description": "Text prompt for transformation"},
            {"name": "input_image_path", "type": "string", "required": True, "description": "Path to input image"},
            {"name": "model", "type": "string", "required": False, "default": "wanx-v1", "description": "Model to use"}
        ]

        bailian_app_params = [
            {"name": "prompt", "type": "string", "required": True, "description": "Input prompt for the Bailian App"},
            {"name": "app_id", "type": "string", "required": False, "description": "Bailian App ID (overrides default config)"}
        ]

        return [
            ToolConfig(name="text2image", description="Generate image from text prompt using DashScope/Wanx", parameters=text2image_params),
            ToolConfig(name="image2image", description="Transform image using DashScope/Wanx", parameters=image2image_params),
            ToolConfig(name="bailian_app", description="Execute a Bailian Application task", parameters=bailian_app_params),
        ]

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

        # Configuration
        ak = server_config.get("access_key_id")
        sk = server_config.get("access_key_secret")
        endpoint = server_config.get("endpoint", "https://bailian.aliyuncs.com")
        agent_key = server_config.get("agent_key")

        if not sk:
            return {"task_id": task_id, "status": "error", "error_message": "AccessKey Secret (API Key) is missing"}

        try:
            if tool_name == "text2image":
                dashscope.api_key = sk
                return await self._execute_text2image(task_id, parameters, progress_callback)
            elif tool_name == "image2image":
                dashscope.api_key = sk
                return await self._execute_image2image(task_id, parameters, task_data.get("resources", []), progress_callback)
            elif tool_name == "bailian_app":
                return await self._execute_bailian_app(task_id, ak, sk, endpoint, agent_key, parameters, progress_callback)
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

    async def _execute_text2image(self, task_id, parameters, progress_callback):
        prompt = parameters.get("prompt", "")
        model = parameters.get("model", "wanx-v1")
        width = parameters.get("width", 1024)
        height = parameters.get("height", 1024)

        progress_callback(10, f"Submitting DashScope task ({model})...", {})

        def call_dashscope():
            return ImageSynthesis.call(
                model=model,
                prompt=prompt,
                size=f"{width}*{height}"
            )

        loop = asyncio.get_event_loop()
        rsp = await loop.run_in_executor(None, call_dashscope)

        if rsp.status_code == 200:
            progress_callback(80, "Generation complete, downloading images...", {})
            output_files = []
            for i, img in enumerate(rsp.output.results):
                url = img.url
                local_path = self.output_dir / f"{task_id}_{i}.png"
                img_data = requests.get(url).content
                with open(local_path, "wb") as f:
                    f.write(img_data)
                output_files.append(str(local_path))
            
            return {"task_id": task_id, "status": "success", "output_files": output_files}
        else:
            raise Exception(f"DashScope error: {rsp.code} - {rsp.message}")

    async def _execute_image2image(self, task_id, parameters, resources, progress_callback):
        prompt = parameters.get("prompt", "")
        model = parameters.get("model", "wanx-v1")
        input_image_path = parameters.get("input_image_path")
        
        # Check resources
        processed_resources = parameters.get("processed_resources")
        if processed_resources:
            input_image_path = processed_resources[0]

        if not input_image_path or not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        progress_callback(10, f"Submitting DashScope i2i task ({model})...", {})

        def call_dashscope_i2i():
            # For Wanx i2i, image_url can be a local file path with file:// prefix
            return ImageSynthesis.call(
                model=model,
                prompt=prompt,
                image_url=f"file://{input_image_path}",
                n=1
            )

        loop = asyncio.get_event_loop()
        rsp = await loop.run_in_executor(None, call_dashscope_i2i)

        if rsp.status_code == 200:
            progress_callback(80, "Generation complete, downloading result...", {})
            output_files = []
            for i, img in enumerate(rsp.output.results):
                url = img.url
                local_path = self.output_dir / f"{task_id}_i2i_{i}.png"
                img_data = requests.get(url).content
                with open(local_path, "wb") as f:
                    f.write(img_data)
                output_files.append(str(local_path))
            
            return {"task_id": task_id, "status": "success", "output_files": output_files}
        else:
            raise Exception(f"DashScope error: {rsp.code} - {rsp.message}")

    async def _execute_bailian_app(self, task_id, ak, sk, endpoint, default_app_id, parameters, progress_callback):
        prompt = parameters.get("prompt", "")
        app_id = parameters.get("app_id") or default_app_id

        if not ak or not sk or not app_id:
            raise Exception("Bailian App execution requires AK, SK and App ID")

        progress_callback(10, f"Connecting to Bailian App ({app_id})...", {})

        def call_bailian_sdk():
            client = AccessTokenClient(access_key_id=ak, access_key_secret=sk)
            token = client.get_token()
            completions = Completions(token=token, endpoint=endpoint)
            return completions.call(app_id=app_id, prompt=prompt)

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, call_bailian_sdk)

        if resp.get("success"):
            text_result = resp.get("data", {}).get("text", "")
            # Save result to a text file
            local_path = self.output_dir / f"{task_id}_result.txt"
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(text_result)
            
            return {
                "task_id": task_id,
                "status": "success",
                "output_files": [str(local_path)],
                "metadata": {"text": text_result}
            }
        else:
            raise Exception(f"Bailian SDK error: {resp.get('error_code')} - {resp.get('error_message')}")

if __name__ == "__main__":
    plugin = BailianServerPlugin()
    plugin.run()
