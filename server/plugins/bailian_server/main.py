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

# Add project root to path to import base_plugin
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from server.plugins.base_plugin import BaseServerPlugin, AbilityConfig
from server.plugins.bailian_server.models_config import models_config, CODING_PLAN_PREFIX

logger = logging.getLogger(__name__)

# Default endpoints (can be overridden by models.yml)
DASHSCOPE_IMAGE_ENDPOINT = models_config.get_dashscope_image_endpoint()

# Try to import SDKs
try:
    import dashscope
    from dashscope import ImageSynthesis
    DASHSCOPE_SDK_AVAILABLE = True
except ImportError:
    DASHSCOPE_SDK_AVAILABLE = False
    logger.warning("dashscope SDK not found, using HTTP API")


class BailianServerPlugin(BaseServerPlugin):
    """
    Plugin for Alibaba Cloud DashScope (Bailian) integration.

    Simplified configuration: Only requires a single API Key.
    """

    def __init__(self, workspace_path: Optional[str] = None):
        super().__init__()
        # Use workspace/project/plugins/bailian as output directory
        if workspace_path:
            self.output_dir = Path(workspace_path) / "plugins" / "bailian"
        else:
            # Fallback to plugin's outputs directory
            self.output_dir = Path(__file__).parent / "outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

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

    def get_supported_abilities(self) -> List[AbilityConfig]:
        """Get list of abilities supported by this plugin with model definitions"""
        # Text-to-Image models (wanx series)
        text2image_models = [
            {
                "name": "wanx2.1-t2i-turbo",
                "display_name": "Wanx 2.1 Turbo",
                "description": "Fast text-to-image generation, suitable for quick iterations",
                "detailed_description": "Wanx 2.1 Turbo is optimized for speed while maintaining good quality. Best for rapid prototyping and iterative design.",
                "tags": ["fast", "turbo", "cost-effective"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "supported_sizes": ["512x512", "720x1280", "1024x1024", "1280x720", "2048x2048"]
                },
                "pricing": {
                    "per_image": 0.008  # ~0.5 cents per image
                },
                "is_default": False
            },
            {
                "name": "wanx2.1-t2i-plus",
                "display_name": "Wanx 2.1 Plus",
                "description": "High quality text-to-image generation",
                "detailed_description": "Wanx 2.1 Plus delivers higher quality images with more detail. Best for final production outputs.",
                "tags": ["high-quality", "plus", "detailed"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "supported_sizes": ["512x512", "720x1280", "1024x1024", "1280x720", "2048x2048"]
                },
                "pricing": {
                    "per_image": 0.016  # ~1.6 cents per image
                },
                "is_default": False
            },
            {
                "name": "wanx2.6-t2i-turbo",
                "display_name": "Wanx 2.6 Turbo",
                "description": "Latest fast text-to-image generation model",
                "tags": ["latest", "fast", "turbo"],
                "specs": {
                    "max_resolution": "2048x2048"
                },
                "pricing": {
                    "per_image": 0.01
                },
                "is_default": False
            },
            {
                "name": "wanx2.6-t2i-plus",
                "display_name": "Wanx 2.6 Plus",
                "description": "Latest high quality text-to-image generation model",
                "tags": ["latest", "high-quality", "plus"],
                "specs": {
                    "max_resolution": "2048x2048"
                },
                "pricing": {
                    "per_image": 0.02
                },
                "is_default": False
            },
        ]

        # Qwen-Image models (new generation using MultiModalConversation API)
        qwen_image_t2i_models = [
            {
                "name": "qwen-image-2.0-pro",
                "display_name": "Qwen Image 2.0 Pro",
                "description": "Latest Qwen image generation Pro series with enhanced text rendering, realistic textures, and semantic adherence",
                "tags": ["latest", "pro", "recommended", "text-rendering", "high-quality"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "min_resolution": "512x512",
                    "supported_sizes": ["512x512", "1024x1024", "1280x720", "720x1280", "2048x2048"],
                    "max_images": 6,
                    "min_images": 1,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.05  # TBD - placeholder
                },
                "is_default": True
            },
            {
                "name": "qwen-image-2.0-pro-2026-03-03",
                "display_name": "Qwen Image 2.0 Pro 2026-03-03",
                "description": "Qwen image generation Pro series (snapshot 2026-03-03)",
                "tags": ["pro", "snapshot"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.05
                },
                "is_default": False
            },
            {
                "name": "qwen-image-2.0",
                "display_name": "Qwen Image 2.0",
                "description": "Qwen image generation accelerated version, balancing quality and speed",
                "tags": ["latest", "fast", "accelerated"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.03
                },
                "is_default": False
            },
            {
                "name": "qwen-image-2.0-2026-03-03",
                "display_name": "Qwen Image 2.0 2026-03-03",
                "description": "Qwen image generation (snapshot 2026-03-03)",
                "tags": ["snapshot"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.03
                },
                "is_default": False
            },
            {
                "name": "qwen-image-max",
                "display_name": "Qwen Image Max",
                "description": "Qwen image generation Max series with stronger realism and naturalness, lower AI artifacts",
                "tags": ["max", "high-quality", "realistic"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 1,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.08
                },
                "is_default": False
            },
            {
                "name": "qwen-image-max-2025-12-30",
                "display_name": "Qwen Image Max 2025-12-30",
                "description": "Qwen image generation Max series (snapshot 2025-12-30)",
                "tags": ["max", "snapshot"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 1,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.08
                },
                "is_default": False
            },
            {
                "name": "qwen-image-plus",
                "display_name": "Qwen Image Plus",
                "description": "Qwen image generation Plus series, excels at diverse artistic styles and text rendering",
                "tags": ["plus", "artistic", "text-rendering"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.04
                },
                "is_default": False
            },
            {
                "name": "qwen-image-plus-2026-01-09",
                "display_name": "Qwen Image Plus 2026-01-09",
                "description": "Qwen image generation Plus series (snapshot 2026-01-09)",
                "tags": ["plus", "snapshot"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.04
                },
                "is_default": False
            },
            {
                "name": "qwen-image",
                "display_name": "Qwen Image",
                "description": "Qwen image generation base model",
                "tags": ["base"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image"
                },
                "pricing": {
                    "per_image": 0.02
                },
                "is_default": False
            },
        ]

        # Image-to-Image models (wanx series)
        image2image_models = [
            {
                "name": "wanx2.1-i2i-turbo",
                "display_name": "Wanx 2.1 I2I Turbo",
                "description": "Fast image-to-image transformation",
                "tags": ["fast", "turbo"],
                "specs": {
                    "max_resolution": "2048x2048"
                },
                "pricing": {
                    "per_image": 0.012
                },
                "is_default": False
            },
            {
                "name": "wanx2.1-i2i-plus",
                "display_name": "Wanx 2.1 I2I Plus",
                "description": "High quality image-to-image transformation",
                "tags": ["high-quality", "plus"],
                "specs": {
                    "max_resolution": "2048x2048"
                },
                "pricing": {
                    "per_image": 0.02
                },
                "is_default": False
            },
        ]

        # Qwen-Image Edit models
        qwen_image_i2i_models = [
            {
                "name": "qwen-image-edit-max",
                "display_name": "Qwen Image Edit Max",
                "description": "Qwen image editing Max series with stronger industrial design, geometric reasoning, and character consistency",
                "tags": ["max", "edit", "recommended", "industrial-design", "geometric"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "min_resolution": "512x512",
                    "max_images": 6,
                    "min_images": 1,
                    "api_type": "qwen-image-edit"
                },
                "pricing": {
                    "per_image": 0.08
                },
                "is_default": True
            },
            {
                "name": "qwen-image-edit-max-2026-01-16",
                "display_name": "Qwen Image Edit Max 2026-01-16",
                "description": "Qwen image editing Max series (snapshot 2026-01-16)",
                "tags": ["max", "edit", "snapshot"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image-edit"
                },
                "pricing": {
                    "per_image": 0.08
                },
                "is_default": False
            },
            {
                "name": "qwen-image-edit-plus",
                "display_name": "Qwen Image Edit Plus",
                "description": "Qwen image editing Plus series with multi-image output and custom resolution support",
                "tags": ["plus", "edit", "multi-output"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image-edit"
                },
                "pricing": {
                    "per_image": 0.05
                },
                "is_default": False
            },
            {
                "name": "qwen-image-edit-plus-2025-12-15",
                "display_name": "Qwen Image Edit Plus 2025-12-15",
                "description": "Qwen image editing Plus series (snapshot 2025-12-15)",
                "tags": ["plus", "edit", "snapshot"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image-edit"
                },
                "pricing": {
                    "per_image": 0.05
                },
                "is_default": False
            },
            {
                "name": "qwen-image-edit-plus-2025-10-30",
                "display_name": "Qwen Image Edit Plus 2025-10-30",
                "description": "Qwen image editing Plus series (snapshot 2025-10-30)",
                "tags": ["plus", "edit", "snapshot"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 6,
                    "api_type": "qwen-image-edit"
                },
                "pricing": {
                    "per_image": 0.05
                },
                "is_default": False
            },
            {
                "name": "qwen-image-edit",
                "display_name": "Qwen Image Edit",
                "description": "Qwen image editing base model, supports single image editing and multi-image fusion",
                "tags": ["base", "edit"],
                "specs": {
                    "max_resolution": "2048x2048",
                    "max_images": 1,
                    "api_type": "qwen-image-edit"
                },
                "pricing": {
                    "per_image": 0.03
                },
                "is_default": False
            },
        ]

        # Chat completion models with pricing (LLMs)
        chat_models = [
            # Flagship models
            {
                "name": "qwen-max",
                "display_name": "Qwen Max",
                "description": "Most capable model for complex tasks",
                "detailed_description": "Qwen Max is the flagship model with best overall performance for complex reasoning, analysis, and creative tasks.",
                "tags": ["flagship", "complex-tasks", "reasoning"],
                "specs": {
                    "context_length": 32768,
                    "supports_vision": False
                },
                "pricing": {
                    "per_input_token": 0.002,   # $0.002 per 1K input tokens
                    "per_output_token": 0.006   # $0.006 per 1K output tokens
                },
                "is_default": True
            },
            {
                "name": "qwen-plus",
                "display_name": "Qwen Plus",
                "description": "Balanced model with good capability and speed",
                "tags": ["balanced", "efficient"],
                "specs": {
                    "context_length": 131072,
                    "supports_vision": False
                },
                "pricing": {
                    "per_input_token": 0.0004,
                    "per_output_token": 0.0012
                },
                "is_default": False
            },
            {
                "name": "qwen-turbo",
                "display_name": "Qwen Turbo",
                "description": "Fast and efficient model",
                "tags": ["fast", "efficient"],
                "specs": {
                    "context_length": 131072,
                    "supports_vision": False
                },
                "pricing": {
                    "per_input_token": 0.0003,
                    "per_output_token": 0.0006
                },
                "is_default": False
            },
            {
                "name": "qwen-flash",
                "display_name": "Qwen Flash",
                "description": "Ultra-fast model for simple tasks",
                "tags": ["ultra-fast", "simple-tasks"],
                "specs": {
                    "context_length": 128000,
                    "supports_vision": False
                },
                "pricing": {
                    "per_input_token": 0.0001,
                    "per_output_token": 0.0003
                },
                "is_default": False
            },
            # Vision models
            {
                "name": "qwen-vl-max",
                "display_name": "Qwen VL Max",
                "description": "Vision-language model (most capable)",
                "tags": ["vision", "multimodal", "flagship"],
                "specs": {
                    "context_length": 32768,
                    "supports_vision": True
                },
                "pricing": {
                    "per_input_token": 0.002,
                    "per_output_token": 0.006
                },
                "is_default": False
            },
            {
                "name": "qwen-vl-plus",
                "display_name": "Qwen VL Plus",
                "description": "Vision-language model (balanced)",
                "tags": ["vision", "multimodal", "balanced"],
                "specs": {
                    "context_length": 32768,
                    "supports_vision": True
                },
                "pricing": {
                    "per_input_token": 0.0008,
                    "per_output_token": 0.002
                },
                "is_default": False
            },
            # Reasoning model
            {
                "name": "qwq-plus",
                "display_name": "QwQ Plus",
                "description": "Reasoning model for complex reasoning tasks",
                "tags": ["reasoning", "complex"],
                "specs": {
                    "context_length": 131072,
                    "supports_vision": False
                },
                "pricing": {
                    "per_input_token": 0.001,
                    "per_output_token": 0.003
                },
                "is_default": False
            },
            # Coder model
            {
                "name": "qwen-coder",
                "display_name": "Qwen Coder",
                "description": "Code-specialized model for programming tasks",
                "tags": ["code", "programming", "specialized"],
                "specs": {
                    "context_length": 131072,
                    "supports_vision": False
                },
                "pricing": {
                    "per_input_token": 0.0005,
                    "per_output_token": 0.001
                },
                "is_default": False
            },
        ]

        # Parameter definitions
        text2image_params = [
            {"name": "prompt", "type": "string", "required": True,
             "description": "Text prompt for image generation"},
            {"name": "model", "type": "string", "required": False,
             "default": "qwen-image-2.0-pro",
             "description": "Model: qwen-image-2.0-pro, wanx2.1-t2i-turbo, wanx2.1-t2i-plus, etc."},
            {"name": "width", "type": "integer", "required": False,
             "default": 1024, "description": "Image width (512-2048)"},
            {"name": "height", "type": "integer", "required": False,
             "default": 1024, "description": "Image height (512-2048)"},
            {"name": "n", "type": "integer", "required": False,
             "default": 1, "description": "Number of images to generate (1-6, for qwen-image models only)"}
        ]

        image2image_params = [
            {"name": "prompt", "type": "string", "required": True,
             "description": "Text prompt for transformation"},
            {"name": "model", "type": "string", "required": False,
             "default": "qwen-image-edit-max",
             "description": "Model: qwen-image-edit-max, wanx2.1-i2i-turbo, etc."},
            {"name": "n", "type": "integer", "required": False,
             "default": 1, "description": "Number of images to generate (1-6, for qwen-image-edit models only)"}
        ]

        # Image edit params (for inpainting, outpainting, etc.)
        imageedit_params = [
            {"name": "prompt", "type": "string", "required": True,
             "description": "Text prompt for image editing"},
            {"name": "model", "type": "string", "required": False,
             "default": "qwen-image-edit-max",
             "description": "Model: qwen-image-edit-max, qwen-image-edit-plus, etc."},
            {"name": "n", "type": "integer", "required": False,
             "default": 1, "description": "Number of images to generate (1-6)"}
        ]

        chat_completion_params = [
            {"name": "model", "type": "string", "required": False,
             "default": "qwen-max",
             "description": "Model: qwen-max, qwen-plus, qwen-turbo, qwen-vl-max, qwq-plus"},
            {"name": "messages", "type": "array", "required": True,
             "description": "Chat messages in OpenAI format"},
            {"name": "temperature", "type": "float", "required": False,
             "default": 0.7, "description": "Sampling temperature (0-2)"},
            {"name": "max_tokens", "type": "integer", "required": False,
             "default": 4096, "description": "Maximum tokens in response"},
            {"name": "stream", "type": "boolean", "required": False,
             "default": False, "description": "Enable streaming response"},
        ]

        # Combine wanx and qwen-image models for text2image
        all_text2image_models = text2image_models + qwen_image_t2i_models

        # Combine wanx and qwen-image edit models for image2image
        all_image2image_models = image2image_models + qwen_image_i2i_models

        return [
            AbilityConfig(
                name="text2image",
                description="Generate image from text using Wanx or Qwen-Image model",
                parameters=text2image_params,
                models=all_text2image_models
            ),
            AbilityConfig(
                name="image2image",
                description="Transform image using Wanx or Qwen-Image model (reference based generation)",
                parameters=image2image_params,
                models=all_image2image_models
            ),
            AbilityConfig(
                name="imageedit",
                description="Edit image using Qwen-Image-Edit model (inpainting, outpainting, etc.)",
                parameters=imageedit_params,
                models=qwen_image_i2i_models
            ),
            AbilityConfig(
                name="chat_completion",
                description="LLM chat via DashScope OpenAI-compatible API",
                parameters=chat_completion_params,
                models=chat_models
            ),
        ]

    async def execute_task(
        self,
        task_data: Dict[str, Any],
        progress_callback: Callable[[float, str, Dict[str, Any]], None]
    ) -> Dict[str, Any]:
        """Execute a task based on its capability type."""
        task_id = task_data.get("task_id", "unknown")
        ability = task_data.get("ability") or task_data.get("capability", "")
        parameters = task_data.get("parameters", {})
        metadata = task_data.get("metadata", {})
        server_config = metadata.get("server_config", {})

        # Get workspace_path from metadata and update output directory
        workspace_path = metadata.get("workspace_path")
        if workspace_path:
            # Use workspace/plugins/bailian as output directory
            self.output_dir = Path(workspace_path) / "plugins" / "bailian"
            self.output_dir.mkdir(parents=True, exist_ok=True)

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

        # Log task parameters for debugging
        model = parameters.get("model", default_image_model)
        width = parameters.get("width", 1024)
        height = parameters.get("height", 1024)
        prompt = parameters.get("prompt", "")
        n = parameters.get("n", 1)
        logger.info(f"[Bailian] {ability} task: task_id={task_id}, model={model}, size={width}x{height}, n={n}")
        logger.info(f"[Bailian] prompt={prompt[:200]}...")

        try:
            if ability == "text2image":
                return await self._execute_text2image(
                    task_id, api_key, parameters, default_image_model, progress_callback
                )
            elif ability == "image2image":
                return await self._execute_image2image(
                    task_id, api_key, parameters, task_data.get("resources", []),
                    default_image_model, progress_callback
                )
            elif ability == "imageedit":
                return await self._execute_imageedit(
                    task_id, api_key, parameters, task_data.get("resources", []),
                    default_image_model, progress_callback
                )
            elif ability == "chat_completion":
                return await self._execute_chat_completion(
                    task_id, api_key, parameters, default_model,
                    coding_plan_enabled, coding_plan_api_key, progress_callback
                )
            else:
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error_message": f"Unsupported ability: {ability}",
                    "output_files": []
                }

        except Exception as e:
            logger.error(f"Error executing task with ability {ability}: {e}", exc_info=True)
            return {
                "task_id": task_id,
                "status": "error",
                "error_message": str(e),
                "output_files": []
            }

    def _is_qwen_image_model(self, model: str) -> bool:
        """Check if model is a qwen-image model"""
        return model.startswith("qwen-image") and not model.startswith("qwen-image-edit")

    def _is_qwen_image_edit_model(self, model: str) -> bool:
        """Check if model is a qwen-image-edit model"""
        return model.startswith("qwen-image-edit")

    async def _execute_text2image(
        self, task_id, api_key, parameters, default_model, progress_callback
    ):
        """Execute text-to-image generation using DashScope API."""
        prompt = parameters.get("prompt", "")
        model = parameters.get("model", default_model)
        width = parameters.get("width", 1024)
        height = parameters.get("height", 1024)
        n = parameters.get("n", 1)  # Number of images to generate for qwen-image

        progress_callback(10, f"Submitting image generation task ({model})...", {})

        # Check if this is a qwen-image model
        if self._is_qwen_image_model(model):
            return await self._execute_qwen_image_text2image(
                task_id, api_key, model, prompt, width, height, n, progress_callback
            )

        # Use wanx (ImageSynthesis) API for other models
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

    async def _execute_qwen_image_text2image(
        self, task_id, api_key, model, prompt, width, height, n, progress_callback
    ):
        """Execute text-to-image using qwen-image model via MultiModalConversation API."""
        from dashscope import MultiModalConversation
        import mimetypes

        # Log model and prompt for debugging
        logger.info(f"[Bailian Text2Image] task_id={task_id}, model={model}, size={width}x{height}, n={n}")
        logger.info(f"[Bailian Text2Image] prompt={prompt[:200]}...")

        progress_callback(20, f"Calling Qwen-Image API ({model})...", {})

        # Build messages in the format required by MultiModalConversation
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": prompt}
                ]
            }
        ]

        # Prepare parameters
        size = f"{width}*{height}"

        def call_qwen_image():
            return MultiModalConversation.call(
                api_key=api_key,
                model=model,
                messages=messages,
                result_format='message',
                stream=False,
                watermark=False,
                prompt_extend=True,
                negative_prompt=" ",
                size=size,
                n=n
            )

        loop = asyncio.get_event_loop()
        rsp = await loop.run_in_executor(None, call_qwen_image)

        if rsp.status_code == 200:
            # Extract image URLs from response
            results = []
            for content in rsp.output.choices[0].message.content:
                if 'image' in content:
                    image_url = content['image']
                    results.append({"url": image_url})

            if results:
                return await self._download_images_from_urls(task_id, results, progress_callback)
            else:
                raise Exception("No images in response from Qwen-Image API")
        else:
            raise Exception(f"Qwen-Image API error: {rsp.code} - {rsp.message}")

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

        # SSL context that skips verification (for development)
        ssl_context = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(connector=ssl_context) as session:
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
        n = parameters.get("n", 1)  # Number of images to generate for qwen-image-edit

        # Get input image path
        input_image_path = parameters.get("input_image_path")
        processed_resources = parameters.get("processed_resources")

        if processed_resources:
            input_image_path = processed_resources[0]

        if not input_image_path or not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        progress_callback(10, f"Submitting image-to-image task ({model})...", {})

        # Check if this is a qwen-image-edit model
        if self._is_qwen_image_edit_model(model):
            return await self._execute_qwen_image_edit(
                task_id, api_key, model, prompt, input_image_path, n, progress_callback
            )

        # Use wanx (ImageSynthesis) API for other models
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

    async def _execute_imageedit(
        self, task_id, api_key, parameters, resources, default_model, progress_callback
    ):
        """Execute image editing (inpainting, outpainting, etc.) using qwen-image-edit model."""
        prompt = parameters.get("prompt", "")
        model = parameters.get("model", "qwen-image-edit-max")
        n = parameters.get("n", 1)

        # Get input image path
        input_image_path = parameters.get("input_image_path")
        processed_resources = parameters.get("processed_resources")

        if processed_resources:
            input_image_path = processed_resources[0]

        if not input_image_path or not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        progress_callback(10, f"Submitting image edit task ({model})...", {})

        # Use qwen-image-edit model for image editing
        return await self._execute_qwen_image_edit(
            task_id, api_key, model, prompt, input_image_path, n, progress_callback
        )

    def _encode_image_base64(self, file_path: str) -> str:
        """Encode image file to base64 data URL format"""
        import mimetypes
        import base64

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type or not mime_type.startswith("image/"):
            raise ValueError(f"Unsupported or unrecognized image format: {file_path}")

        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:{mime_type};base64,{encoded_string}"

    async def _execute_qwen_image_edit(
        self, task_id, api_key, model, prompt, input_image_path, n, progress_callback
    ):
        """Execute image-to-image using qwen-image-edit model via MultiModalConversation API."""
        from dashscope import MultiModalConversation

        # Log model and prompt for debugging
        logger.info(f"[Bailian ImageEdit] task_id={task_id}, model={model}, n={n}")
        logger.info(f"[Bailian ImageEdit] prompt={prompt[:200]}...")
        logger.info(f"[Bailian ImageEdit] input_image={input_image_path}")

        progress_callback(20, f"Calling Qwen-Image Edit API ({model})...", {})

        # Encode input image to base64
        image_base64 = self._encode_image_base64(input_image_path)

        # Build messages with the input image
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image_base64},
                    {"text": prompt}
                ]
            }
        ]

        def call_qwen_image_edit():
            return MultiModalConversation.call(
                api_key=api_key,
                model=model,
                messages=messages,
                result_format='message',
                stream=False,
                watermark=False,
                prompt_extend=True,
                negative_prompt=" ",
                n=n
            )

        loop = asyncio.get_event_loop()
        rsp = await loop.run_in_executor(None, call_qwen_image_edit)

        if rsp.status_code == 200:
            # Extract image URLs from response
            results = []
            for content in rsp.output.choices[0].message.content:
                if 'image' in content:
                    image_url = content['image']
                    results.append({"url": image_url})

            if results:
                return await self._download_images_from_urls(task_id, results, progress_callback)
            else:
                raise Exception("No images in response from Qwen-Image Edit API")
        else:
            raise Exception(f"Qwen-Image Edit API error: {rsp.code} - {rsp.message}")

    async def _execute_chat_completion(
        self, task_id, api_key, parameters, default_model,
        coding_plan_enabled, coding_plan_api_key, progress_callback
    ):
        """Execute chat completion via DashScope SDK directly (no LiteLLM)."""
        if not DASHSCOPE_SDK_AVAILABLE:
            raise RuntimeError("dashscope SDK is required for chat_completion. Install with: pip install dashscope")

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

        # DEBUG: Log API key info
        logger.warning(
            f"[DEBUG] Chat completion: model={model}, actual_model={actual_model}, "
            f"is_coding_plan={is_coding_plan_model}, coding_plan_enabled={coding_plan_enabled}, "
            f"has_coding_plan_key={bool(coding_plan_api_key)}"
        )

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
            # Use Coding Plan API key and base URL
            use_api_key = coding_plan_api_key
            # Set Coding Plan base URL
            dashscope.base_http_api_url = "https://coding.dashscope.aliyuncs.com/v1"
            dashscope.base_websocket_api_url = "https://coding.dashscope.aliyuncs.com/api-ws/v1/inference"
            logger.warning(f"[DEBUG] Using Coding Plan API key: {use_api_key[:10]}... and base URL: {dashscope.base_http_api_url}")
            progress_callback(10, f"Calling Coding Plan ({actual_model})...", {})
        else:
            # Use standard DashScope API key
            use_api_key = api_key
            # Reset to standard base URL
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
            dashscope.base_websocket_api_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
            logger.warning(f"[DEBUG] Using standard API key: {use_api_key[:10]}... and base URL: {dashscope.base_http_api_url}")
            progress_callback(10, f"Calling DashScope LLM ({actual_model})...", {})

        # Set API key for dashscope SDK
        dashscope.api_key = use_api_key

        # For Coding Plan, use OpenAI-compatible API directly via HTTP
        if is_coding_plan_model:
            # Use OpenAI-compatible API for Coding Plan
            base_url = "https://coding.dashscope.aliyuncs.com/v1"
            progress_callback(10, f"Calling Coding Plan ({actual_model}) via OpenAI API...", {})

            def call_coding_plan():
                import requests
                import json

                headers = {
                    "Authorization": f"Bearer {use_api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": actual_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": stream,
                }

                url = f"{base_url}/chat/completions"

                if stream:
                    # Streaming response
                    full_content = []
                    response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
                    if response.status_code != 200:
                        raise Exception(f"Coding Plan API error: {response.status_code} - {response.text}")

                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(data)
                                    if 'choices' in chunk_data and chunk_data['choices']:
                                        delta = chunk_data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            content = delta['content']
                                            full_content.append(content)
                                            progress_callback(
                                                50, f"Generating... ({len(''.join(full_content))} chars)",
                                                {"partial_content": content}
                                            )
                                except:
                                    pass
                    return {"content": "".join(full_content), "stream": True}
                else:
                    # Non-streaming response
                    response = requests.post(url, headers=headers, json=payload, timeout=60)
                    if response.status_code != 200:
                        raise Exception(f"Coding Plan API error: {response.status_code} - {response.text}")

                    result = response.json()
                    if 'choices' in result and result['choices']:
                        content = result['choices'][0]['message']['content']
                        return {"content": content, "stream": False}
                    raise Exception("No content in response")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, call_coding_plan)

        else:
            # Use dashscope SDK directly for standard models
            from dashscope import Generation

            def call_dashscope():
                if stream:
                    # Streaming response
                    full_content = []
                    response = Generation.call(
                        model=actual_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                        result_format='message'
                    )
                    if response.status_code == 200:
                        for chunk in response:
                            if chunk.code is None and hasattr(chunk, 'choices') and chunk.choices:
                                delta = chunk.choices[0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_content.append(content)
                                    progress_callback(
                                        50, f"Generating... ({len(full_content)} chars)",
                                        {"partial_content": content}
                                    )
                        return {"content": "".join(full_content), "stream": True}
                    else:
                        raise Exception(f"DashScope API error: {response.code} - {response.message}")
                else:
                    # Non-streaming response
                    response = Generation.call(
                        model=actual_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        result_format='message'
                    )
                    if response.status_code == 200:
                        content = response.output.choices[0].message.content
                        return {"content": content, "stream": False}
                    else:
                        raise Exception(f"DashScope API error: {response.code} - {response.message}")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, call_dashscope)

        result_text = result["content"]

        progress_callback(90, "Chat completion done", {})

        # Note: Don't save chat results to file - text is returned directly in metadata
        # This avoids accumulating chat log files that are not needed for chat completion

        # Extract usage info if available
        usage = {}

        return {
            "task_id": task_id,
            "status": "success",
            "output_files": [],
            "metadata": {
                "text": result_text,
                "model": model,
                "actual_model": actual_model,
                "usage": usage,
            }
        }



if __name__ == "__main__":
    plugin = BailianServerPlugin()
    plugin.run()
