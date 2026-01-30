"""
Text2Image Demo Plugin

A simple demo plugin that generates placeholder images with text.
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional

# Add parent directory to path to import base_plugin
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.plugins.base_plugin import BaseServerPlugin, ToolConfig

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: PIL (Pillow) is required. Install with: pip install Pillow")
    sys.exit(1)


class LocalServerPlugin(BaseServerPlugin):
    """
    Local Server plugin for AI services.

    This plugin provides built-in AI services running locally.
    """

    def __init__(self):
        super().__init__()
        self.output_dir = Path(__file__).parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)

    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin metadata"""
        return {
            "name": "Local Server",
            "version": "1.0.0",
            "description": "Local sever supporting multiple tools",
            "author": "Filmeto Team"
        }

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
            # Import the default config widget
            from app.ui.server_list.default_config_widget import DefaultConfigWidget

            # Create and return the widget using the plugin info and config
            widget = DefaultConfigWidget(self.get_plugin_info(), server_config, None)
            return widget
        except Exception as e:
            logger.error(f"Failed to create LocalServer config widget: {e}", exc_info=True)
            return None

    def get_supported_tools(self) -> List[ToolConfig]:
        """Get list of tools supported by this plugin with their configs"""
        # Define tools supported by this plugin
        text2image_params = [
            {
                "name": "prompt",
                "type": "string",
                "required": True,
                "description": "Text prompt for generation"
            },
            {
                "name": "negative_prompt",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Negative prompt"
            },
            {
                "name": "width",
                "type": "integer",
                "required": False,
                "default": 512,
                "min": 256,
                "max": 2048,
                "description": "Image width"
            },
            {
                "name": "height",
                "type": "integer",
                "required": False,
                "default": 512,
                "min": 256,
                "max": 2048,
                "description": "Image height"
            },
            {
                "name": "steps",
                "type": "integer",
                "required": False,
                "default": 20,
                "min": 1,
                "max": 100,
                "description": "Number of generation steps"
            }
        ]

        image2image_params = [
            {
                "name": "prompt",
                "type": "string",
                "required": True,
                "description": "Text prompt for transformation"
            },
            {
                "name": "strength",
                "type": "float",
                "required": False,
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Strength of transformation"
            }
        ]

        return [
            ToolConfig(name="text2image", description="Generate image from text prompt", parameters=text2image_params),
            ToolConfig(name="image2image", description="Transform image based on text prompt", parameters=image2image_params)
        ]
    
    async def execute_task(
        self,
        task_data: Dict[str, Any],
        progress_callback: Callable[[float, str, Dict[str, Any]], None]
    ) -> Dict[str, Any]:
        """
        Execute a task based on its tool type.

        Args:
            task_data: Task parameters including tool, parameters, resources
            progress_callback: Callback for reporting progress

        Returns:
            Result dictionary with output files
        """
        task_id = task_data.get("task_id", "unknown")
        tool_name = task_data.get("tool", "")
        parameters = task_data.get("parameters", {})

        try:
            if tool_name == "text2image":
                return await self._execute_text2image_task(task_id, parameters, progress_callback)
            elif tool_name == "image2image":
                return await self._execute_image2image_task(task_id, parameters, progress_callback)
            else:
                return {
                    "task_id": task_id,
                    "status": "error",
                    "error_message": f"Unsupported tool: {tool_name}",
                    "output_files": []
                }

        except Exception as e:
            print(f"Error executing task with tool {tool_name}: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "error_message": str(e),
                "output_files": []
            }

    async def _execute_text2image_task(
        self,
        task_id: str,
        parameters: Dict[str, Any],
        progress_callback: Callable[[float, str, Dict[str, Any]], None]
    ) -> Dict[str, Any]:
        """
        Execute text-to-image generation task.

        Args:
            task_id: Task identifier
            parameters: Task parameters including prompt, width, height, etc.
            progress_callback: Callback for reporting progress

        Returns:
            Result dictionary with output files
        """
        # Extract parameters
        prompt = parameters.get("prompt", "")
        negative_prompt = parameters.get("negative_prompt", "")
        width = parameters.get("width", 512)
        height = parameters.get("height", 512)
        steps = parameters.get("steps", 20)

        print(f"Generating image: {prompt} ({width}x{height})")

        # Report initialization
        progress_callback(0, "Initializing text-to-image generation...", {})
        await asyncio.sleep(0.5)

        # Simulate generation steps
        for step in range(steps):
            # Calculate progress
            percent = (step + 1) / steps * 100
            message = f"Generation step {step+1}/{steps}"

            # Report progress
            progress_callback(percent, message, {"step": step + 1, "total_steps": steps})

            # Simulate processing time
            await asyncio.sleep(0.1)

        # Generate the actual image
        progress_callback(95, "Finalizing image...", {})
        output_path = await self._generate_image(prompt, width, height, task_id)

        # Return result
        return {
            "task_id": task_id,
            "status": "success",
            "output_files": [str(output_path)],
            "output_resources": [
                {
                    "type": "image",
                    "path": str(output_path),
                    "mime_type": "image/png",
                    "size": output_path.stat().st_size,
                    "metadata": {
                        "width": width,
                        "height": height,
                        "prompt": prompt,
                        "negative_prompt": negative_prompt
                    }
                }
            ],
            "metadata": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps
            }
        }

    async def _execute_image2image_task(
        self,
        task_id: str,
        parameters: Dict[str, Any],
        progress_callback: Callable[[float, str, Dict[str, Any]], None]
    ) -> Dict[str, Any]:
        """
        Execute image-to-image transformation task.

        Args:
            task_id: Task identifier
            parameters: Task parameters including prompt, strength, etc.
            progress_callback: Callback for reporting progress

        Returns:
            Result dictionary with output files
        """
        # Extract parameters
        prompt = parameters.get("prompt", "")
        strength = parameters.get("strength", 0.7)

        print(f"Transforming image with prompt: {prompt}, strength: {strength}")

        # Report initialization
        progress_callback(0, "Initializing image-to-image transformation...", {})
        await asyncio.sleep(0.2)

        # Simulate transformation steps
        total_steps = 10
        for step in range(total_steps):
            # Calculate progress
            percent = (step + 1) / total_steps * 100
            message = f"Transformation step {step+1}/{total_steps}"

            # Report progress
            progress_callback(percent, message, {"step": step + 1, "total_steps": total_steps})

            # Simulate processing time
            await asyncio.sleep(0.1)

        # Generate the actual image
        progress_callback(95, "Finalizing transformed image...", {})
        # For demo purposes, we'll just generate a new image with the prompt
        width, height = 512, 512  # Using default values
        output_path = await self._generate_image(prompt, width, height, task_id)

        # Return result
        return {
            "task_id": task_id,
            "status": "success",
            "output_files": [str(output_path)],
            "output_resources": [
                {
                    "type": "image",
                    "path": str(output_path),
                    "mime_type": "image/png",
                    "size": output_path.stat().st_size,
                    "metadata": {
                        "prompt": prompt,
                        "strength": strength
                    }
                }
            ],
            "metadata": {
                "prompt": prompt,
                "strength": strength
            }
        }
    
    async def _generate_image(
        self,
        prompt: str,
        width: int,
        height: int,
        task_id: str
    ) -> Path:
        """
        Generate a demo image with the prompt text.
        
        Args:
            prompt: Text prompt
            width: Image width
            height: Image height
            task_id: Task identifier for filename
        
        Returns:
            Path to generated image
        """
        # Create output filename
        timestamp = int(time.time())
        output_filename = f"{task_id}_{timestamp}.png"
        output_path = self.output_dir / output_filename
        
        # Create image with gradient background
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        # Create gradient background
        for y in range(height):
            # Color gradient from blue to purple
            r = int(100 + (y / height) * 100)
            g = int(50 + (y / height) * 50)
            b = int(200 - (y / height) * 50)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add text
        # Try to use a nice font, fall back to default if not available
        try:
            # Try different font paths
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:\\Windows\\Fonts\\arial.ttf",  # Windows
            ]
            
            font_size = max(20, min(width, height) // 20)
            font = None
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Add prompt text in the center
        text_bbox = draw.textbbox((0, 0), prompt, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2
        
        # Draw text with shadow
        draw.text((text_x + 2, text_y + 2), prompt, fill=(0, 0, 0), font=font)
        draw.text((text_x, text_y), prompt, fill=(255, 255, 255), font=font)
        
        # Add small label at bottom
        label = f"Demo Plugin | {width}x{height}"
        label_bbox = draw.textbbox((0, 0), label, font=font)
        label_width = label_bbox[2] - label_bbox[0]
        draw.text(
            ((width - label_width) // 2, height - 40),
            label,
            fill=(255, 255, 255),
            font=font
        )
        
        # Save image
        image.save(output_path, 'PNG')
        print(f"Saved image to: {output_path}")
        
        return output_path


if __name__ == "__main__":
    # Create and run the plugin
    plugin = LocalServerPlugin()
    plugin.run()

