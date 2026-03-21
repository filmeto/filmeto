"""
Bailian Server Plugin

Integrates Alibaba Cloud DashScope (Bailian) AI services.
Supports text-to-image, image-to-image, and LLM chat completion tools.

Configuration: Only requires a single DashScope API Key.
Get your API Key from: https://bailian.console.aliyun.com/ -> API-KEY管理
"""

import os
import sys
import time
import asyncio
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional

# Add parent directory to path to import base_plugin
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.plugins.base_plugin import BaseServerPlugin, ToolConfig
from server.plugins.bailian_server.models_config import models_config, CODING_PLAN_PREFIX

logger = logging.getLogger(__name__)

# Try to import SDKs
try:
    import dashscope
    from dashscope import ImageSynthesis
    DASHSCOPE_SDK_AVAILABLE = True
except ImportError:
    DASHSCOPE_SDK_AVAILABLE = False
    logger.warning("dashscope SDK not found, using HTTP API")

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("litellm not found, chat_completion tool unavailable")


class BailianServerPlugin(BaseServerPlugin):
    """
    Plugin for Alibaba Cloud DashScope (Bailian) integration.

    Simplified configuration: Only requires a single API Key.
    """

    def __init__(self):
        super().__init__()
        self.output_dir = Path(__file__).parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)

    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin metadata"""
        return {
            "name": "Bailian Server",
            "version": "1.4.0",
            "description": "Alibaba Cloud DashScope integration - Only API Key needed",
            "author": "Filmeto Team",
            "engine": "bailian"
        }

    def init_ui(self, workspace_path: str, server_config: Optional[Dict[str, Any]] = None):
        """Initialize custom UI widget for server configuration."""
        try:
            from server.plugins.bailian_server.config.bailian_config_widget import BailianConfigWidget
            return BailianConfigWidget(workspace_path, server_config)
        except Exception as e:
            print(f"Failed to create Bailian config widget: {e}")
            return None

    def get_supported_tools(self) -> List[ToolConfig]:
        """Get list of tools supported by this plugin"""
        text2image_params = [
            {"name": "prompt", "type": "string", "required": True,
             "description": "Text prompt for image generation"},
            {"name": "model", "type": "string", "required": False,
             "default": "wanx2.1-t2i-turbo",
             "description": "Model: wanx2.1-t2i-turbo, wanx2.1-t2i-plus"},
            {"name": "width", "type": "integer", "required": False,
             "default": 1024, "description": "Image width (512-2048)"},
            {"name": "height", "type": "integer", "required": False,
             "default": 1024, "description": "Image height (512-2048)"}
        ]

        image2image_params = [
            {"name": "prompt", "type": "string", "required": True,
             "description": "Text prompt for transformation"},
            {"name": "model", "type": "string", "required": False,
             "default": "wanx2.1-i2i-turbo",
             "description": "Model for image-to-image"}
        ]

        chat_completion_params = [
            {"name": "model", "type": "string", "required": False,
             "default": "qwen-max",
             "description": "Model: qwen-max, qwen-plus, qwen-turbo, qwen2.5-72b-instruct"},
            {"name": "messages", "type": "array", "required": True,
             "description": "Chat messages in OpenAI format"},
            {"name": "temperature", "type": "float", "required": False,
             "default": 0.7, "description": "Sampling temperature (0-2)"},
            {"name": "max_tokens", "type": "integer", "required": False,
             "default": 4096, "description": "Maximum tokens in response"},
            {"name": "stream", "type": "boolean", "required": False,
             "default": False, "description": "Enable streaming response"},
        ]

        return [
            ToolConfig(name="text2image",
                      description="Generate image from text using Wanx model",
                      parameters=text2image_params),
            ToolConfig(name="image2image",
                      description="Transform image using Wanx model",
                      parameters=image2image_params),
            ToolConfig(name="chat_completion",
                      description="LLM chat via DashScope OpenAI-compatible API",
                      parameters=chat_completion_params),
        ]

    async def execute_task(
        self,
        task_data: Dict[str, Any],
        progress_callback: Callable[[float, str, Dict[str, Any]], None]
    ) -> Dict[str, Any]:
        """Execute a task based on its tool type."""
        task_id = task_data.get("task_id", "unknown")
        tool_name = task_data.get("tool_name", "")
        parameters = task_data.get("parameters", {})
        metadata = task_data.get("metadata", {})
        server_config = metadata.get("server_config", {})

        # Get API Key - single credential needed
        api_key = server_config.get("api_key")

        if not api_key:
            return {
                "task_id": task_id,
                "status": "error",
                "error_message": "API Key is required. Get it from: 阿里云控制台 -> DashScope -> API-KEY管理"
            }

        # Get optional settings
        default_model = server_config.get("default_model", "qwen-max")
        default_image_model = server_config.get("default_image_model", "wanx2.1-t2i-turbo")

        # Coding Plan settings
        coding_plan_enabled = server_config.get("coding_plan_enabled", False)
        coding_plan_api_key = server_config.get("coding_plan_api_key", "")

        try:
            if tool_name == "text2image":
                return await self._execute_text2image(
                    task_id, api_key, parameters, default_image_model, progress_callback
                )
            elif tool_name == "image2image":
                return await self._execute_image2image(
                    task_id, api_key, parameters, task_data.get("resources", []),
                    default_image_model, progress_callback
                )
            elif tool_name == "chat_completion":
                return await self._execute_chat_completion(
                    task_id, api_key, parameters, default_model,
                    coding_plan_enabled, coding_plan_api_key, progress_callback
                )
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

    async def _execute_text2image(
        self, task_id, api_key, parameters, default_model, progress_callback
    ):
        """Execute text-to-image generation using DashScope API."""
        prompt = parameters.get("prompt", "")
        model = parameters.get("model", default_model)
        width = parameters.get("width", 1024)
        height = parameters.get("height", 1024)

        progress_callback(10, f"Submitting image generation task ({model})...", {})

        # Use SDK if available
        if DASHSCOPE_SDK_AVAILABLE:
            dashscope.api_key = api_key

            def call_dashscope():
                return ImageSynthesis.call(
                    model=model,
                    prompt=prompt,
                    size=f"{width}*{height}"
                )

            loop = asyncio.get_event_loop()
            rsp = await loop.run_in_executor(None, call_dashscope)

            if rsp.status_code == 200:
                return await self._download_images(task_id, rsp.output.results, progress_callback)
            else:
                raise Exception(f"DashScope error: {rsp.code} - {rsp.message}")
        else:
            # Use HTTP API directly
            return await self._text2image_via_http(
                task_id, api_key, model, prompt, width, height, progress_callback
            )

    async def _text2image_via_http(
        self, task_id, api_key, model, prompt, width, height, progress_callback
    ):
        """Text-to-image using HTTP API directly."""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }

        payload = {
            "model": model,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": f"{width}*{height}",
                "n": 1
            }
        }

        progress_callback(20, "Sending request to DashScope...", {})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                DASHSCOPE_IMAGE_ENDPOINT,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DashScope API error: {response.status} - {error_text}")

                result = await response.json()

                # Check if async task
                output = result.get("output", {})
                task_status = output.get("task_status")

                if task_status == "PENDING":
                    # Poll for result
                    task_status_url = output.get("task_status_url") or f"{DASHSCOPE_IMAGE_ENDPOINT}/{result.get('output', {}).get('task_id')}"
                    progress_callback(30, "Waiting for image generation...", {})

                    for _ in range(60):  # Max 60 seconds wait
                        await asyncio.sleep(2)
                        async with session.get(
                            task_status_url,
                            headers={"Authorization": f"Bearer {api_key}"}
                        ) as status_response:
                            status_result = await status_response.json()
                            status = status_result.get("output", {}).get("task_status")

                            if status == "SUCCEEDED":
                                results = status_result.get("output", {}).get("results", [])
                                return await self._download_images_from_urls(
                                    task_id, results, progress_callback
                                )
                            elif status == "FAILED":
                                error_msg = status_result.get("output", {}).get("message", "Unknown error")
                                raise Exception(f"Image generation failed: {error_msg}")

                            progress_callback(40, f"Generating... ({status})", {})

                    raise Exception("Image generation timeout")

                # Direct result
                results = output.get("results", [])
                if results:
                    return await self._download_images_from_urls(task_id, results, progress_callback)

                raise Exception("No results from DashScope API")

    async def _download_images(self, task_id, results, progress_callback):
        """Download images from DashScope SDK results."""
        progress_callback(80, "Downloading generated images...", {})
        output_files = []

        for i, img in enumerate(results):
            url = img.url
            local_path = self.output_dir / f"{task_id}_{i}.png"
            img_data = requests.get(url).content
            with open(local_path, "wb") as f:
                f.write(img_data)
            output_files.append(str(local_path))

        return {"task_id": task_id, "status": "success", "output_files": output_files}

    async def _download_images_from_urls(self, task_id, results, progress_callback):
        """Download images from URL list."""
        import aiohttp

        progress_callback(80, "Downloading generated images...", {})
        output_files = []

        async with aiohttp.ClientSession() as session:
            for i, result in enumerate(results):
                url = result.get("url")
                if not url:
                    continue

                local_path = self.output_dir / f"{task_id}_{i}.png"
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(local_path, "wb") as f:
                            f.write(content)
                        output_files.append(str(local_path))

        return {"task_id": task_id, "status": "success", "output_files": output_files}

    async def _execute_image2image(
        self, task_id, api_key, parameters, resources, default_model, progress_callback
    ):
        """Execute image-to-image transformation."""
        prompt = parameters.get("prompt", "")
        model = parameters.get("model", default_model.replace("-t2i-", "-i2i-"))

        # Get input image path
        input_image_path = parameters.get("input_image_path")
        processed_resources = parameters.get("processed_resources")

        if processed_resources:
            input_image_path = processed_resources[0]

        if not input_image_path or not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        progress_callback(10, f"Submitting image-to-image task ({model})...", {})

        if DASHSCOPE_SDK_AVAILABLE:
            dashscope.api_key = api_key

            def call_dashscope_i2i():
                return ImageSynthesis.call(
                    model=model,
                    prompt=prompt,
                    image_url=f"file://{input_image_path}",
                    n=1
                )

            loop = asyncio.get_event_loop()
            rsp = await loop.run_in_executor(None, call_dashscope_i2i)

            if rsp.status_code == 200:
                return await self._download_images(task_id, rsp.output.results, progress_callback)
            else:
                raise Exception(f"DashScope error: {rsp.code} - {rsp.message}")
        else:
            raise Exception("Image-to-image requires dashscope SDK. Install with: pip install dashscope")

    async def _execute_chat_completion(
        self, task_id, api_key, parameters, default_model,
        coding_plan_enabled, coding_plan_api_key, progress_callback
    ):
        """Execute chat completion via DashScope OpenAI-compatible API."""
        if not LITELLM_AVAILABLE:
            raise RuntimeError("litellm is required for chat_completion. Install with: pip install litellm")

        model = parameters.get("model", default_model)
        messages = parameters.get("messages", [])
        temperature = parameters.get("temperature", 0.7)
        max_tokens = parameters.get("max_tokens", 4096)
        stream = parameters.get("stream", False)

        if not messages:
            raise ValueError("messages parameter is required")

        # Determine if this is a Coding Plan model (check with prefix)
        is_coding_plan_model = models_config.is_coding_plan_model(model)

        # Strip prefix for actual API call
        actual_model = models_config.strip_coding_plan_prefix(model)

        if is_coding_plan_model:
            # Check if Coding Plan is enabled and configured
            if not coding_plan_enabled or not coding_plan_api_key:
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error_message": f"Model '{actual_model}' requires Coding Plan to be enabled. "
                                      f"Please enable Coding Plan and configure the API Key.",
                    "output_files": []
                }
            # Use Coding Plan endpoint and API key
            endpoint = models_config.get_coding_plan_endpoint()
            use_api_key = coding_plan_api_key
            progress_callback(10, f"Calling Coding Plan ({actual_model})...", {})
        else:
            # Use standard DashScope endpoint and API key
            endpoint = models_config.get_dashscope_chat_endpoint()
            use_api_key = api_key
            progress_callback(10, f"Calling DashScope LLM ({actual_model})...", {})

        # For Coding Plan, use openai provider with custom base_url
        if is_coding_plan_model:
            litellm_model = f"openai/{actual_model}"
        else:
            # Use dashscope provider with litellm
            litellm_model = f"dashscope/{actual_model}" if not actual_model.startswith("dashscope/") else actual_model

        params = {
            "model": litellm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "api_key": use_api_key,
            "base_url": endpoint,
        }

        if stream:
            response = await litellm.acompletion(**params)
            full_content = []
            async for chunk in response:
                if hasattr(chunk, "choices") and chunk.choices:
                    delta = getattr(chunk.choices[0], "delta", None)
                    if delta and getattr(delta, "content", None):
                        full_content.append(delta.content)
                        progress_callback(
                            50, f"Generating... ({len(full_content)} chunks)",
                            {"partial_content": delta.content}
                        )

            result_text = "".join(full_content)
        else:
            response = await litellm.acompletion(**params)
            choice = response.choices[0]
            result_text = getattr(choice.message, "content", "") or ""

        progress_callback(90, "Chat completion done", {})

        # Save result
        local_path = self.output_dir / f"{task_id}_chat.txt"
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(result_text)

        # Extract usage info
        usage_obj = getattr(response, "usage", None) if not stream else None
        usage = {}
        if usage_obj:
            usage = {
                "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0),
                "completion_tokens": getattr(usage_obj, "completion_tokens", 0),
                "total_tokens": getattr(usage_obj, "total_tokens", 0),
            }

        return {
            "task_id": task_id,
            "status": "success",
            "output_files": [str(local_path)],
            "metadata": {
                "text": result_text,
                "model": model,
                "usage": usage,
            }
        }


if __name__ == "__main__":
    plugin = BailianServerPlugin()
    plugin.run()
