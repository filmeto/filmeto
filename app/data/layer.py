import os
import asyncio
import logging
import subprocess
import threading
import traceback
from enum import Enum
from typing import Optional, Callable, List, Tuple
from blinker import signal
import cv2
import numpy as np
import shutil

logger = logging.getLogger(__name__)

class LayerType(Enum):
    IMAGE = ("image", "\uE6BC")  # 图片生成图标
    VIDEO = ("video", "\uE6BD")  # 视频图标
    GRAPHIC = ("graphic", "\uE61A")  # 调色板图标
    AUDIO = ("audio", "\uE73B")  # 音频相关图标
    SUBTITLE = ("subtitle", "\uE647")  # 文字图标

    def __init__(self, value: str, icon: str):
        self._value_ = value
        self.icon = icon

    @property
    def value(self) -> str:
        return self._value_


class Layer:

    def __init__(self, layer_id: int, name: str = "", layer_type: LayerType = LayerType.IMAGE,
                 visible: bool = True, locked: bool = False, x: int = 0, y: int = 0, width: int = 0, height: int = 0, 
                 timeline_item = None, layer_manager = None):
        self.id = layer_id
        self.name = name if name else f"图层-{layer_id}"
        self.type = layer_type
        self.visible = visible
        self.locked = locked
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.timeline_item = timeline_item
        self.layer_manager = layer_manager
        # 修复：检查timeline_item是否为None，避免AttributeError
        self.layers_path = self.timeline_item.get_layers_path() if self.timeline_item else None

    def get_layer_path(self) -> str:
        # 修复：检查layers_path是否存在
        if not self.layers_path:
            return None
        if self.type==LayerType.IMAGE:
            return os.path.join(self.layers_path, f"{self.id}.png")
        if self.type==LayerType.VIDEO:
            return os.path.join(self.layers_path, f"{self.id}.mp4")
        return None

    def to_dict(self):
        """
        将图层对象转换为字典格式，用于保存到配置文件
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "visible": self.visible,
            "locked": self.locked,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }

    @classmethod
    def from_dict(cls, data: dict, timeline_item, layer_manager=None):
        """
        从字典数据创建图层对象
        """
        layer_id = data.get("id", 0)
        name = data.get("name", "")
        # 通过值查找对应的枚举项
        layer_type_value = data.get("type", LayerType.IMAGE.value)
        layer_type = next((t for t in LayerType if t.value == layer_type_value), LayerType.IMAGE)
        visible = data.get("visible", True)
        locked = data.get("locked", False)
        x = data.get("x", 0)
        y = data.get("y", 0)
        width = data.get("width", 0)
        height = data.get("height", 0)
        return cls(layer_id, name, layer_type, visible, locked, x, y, width, height, timeline_item, layer_manager)


class LayerManager:

    def __init__(self, layer_changed_signal=None):
        self.layers = None
        self.timeline_item = None
        self.layer_changed = layer_changed_signal or signal('layer_changed')
        self._auto_compose_enabled = True
        
        # Connect to layer_changed signal to trigger auto-composition
        self.layer_changed.connect(self._on_layer_changed, sender=self)

    def load_layers(self, timeline_item):
        self.timeline_item = timeline_item
        logger.info(f"Loading layers for timeline item: {timeline_item.index if timeline_item else 'None'}")
        layers_data = timeline_item.get_config_value("layers") or []
        # 使用字典存储图层，以图层ID为键
        self.layers = {layer_data["id"]: Layer.from_dict(layer_data, timeline_item, self) for layer_data in layers_data}
        logger.info(f"Loaded {len(self.layers)} layers")

    def connect_layer_changed(self, func):
        if self.layer_changed is not None:
            self.layer_changed.connect(func, sender=self)
    
    def set_auto_compose(self, enabled: bool):
        """Enable or disable automatic composition on layer changes"""
        self._auto_compose_enabled = enabled
        logger.info(f"Auto-compose {'enabled' if enabled else 'disabled'} for timeline item {self.timeline_item.index if self.timeline_item else 'None'}")
    
    def _on_layer_changed(self, sender, layer, change_type):
        """Internal handler for layer changes that triggers composition"""
        if not self._auto_compose_enabled:
            return
        
        # Only trigger composition for changes that affect visual output
        if change_type in ['added', 'removed', 'modified']:
            logger.info(f"Layer {change_type}: {layer.id}, triggering composition")
            # Schedule composition asynchronously
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.compose_layers())
                else:
                    # If no event loop is running, log a warning
                    logger.warning("No event loop running, cannot trigger auto-composition")
            except RuntimeError as e:
                logger.warning(f"Could not trigger auto-composition: {e}")

    def _save_layers(self):
        # 按图层ID排序，确保保存顺序一致
        layers_data = [self.layers[layer_id].to_dict() for layer_id in sorted(self.layers.keys())]
        self.timeline_item.set_config_value("layers", layers_data)

    def save_layer(self, layer: Layer):
        """
        Save a layer and trigger the layer_changed signal.
        This method should be called after modifying the layer content.
        
        Args:
            layer: The Layer object to save
        """
        if layer and layer.id in self.layers:
            # Emit the layer_changed signal to notify observers
            if self.timeline_item:
                current_item = self.timeline_item.timeline.get_current_item()
                if current_item and self.timeline_item.index == current_item.index:
                    self.layer_changed.send(self, layer=layer, change_type='modified')

    def add_layer(self, layer_type: LayerType = LayerType.IMAGE) -> Layer:
        # 检查timeline_item是否已加载
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # 生成新的图层ID（基于现有最大ID+1，避免删除后的ID冲突）
        if self.layers:
            existing_ids = list(self.layers.keys())
            new_id = max(existing_ids) + 1
        else:
            new_id = 1
        layers_path = self.timeline_item.layers_path

        # 创建图层对应的文件
        if layer_type == LayerType.VIDEO:
            # 视频图层创建mp4文件 - create a valid minimal black video
            layer = Layer(new_id, f"Layer-{new_id}", layer_type, True, False, 0, 0, 720, 1280, self.timeline_item, self)
            video_path = layer.get_layer_path()
            
            # Create a 1-second black video using OpenCV
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(video_path, fourcc, 8.0, (720, 1280))
            
            # Write 8 black frames (1 second at 8fps)
            black_frame = np.zeros((1280, 720, 3), dtype=np.uint8)
            for _ in range(8):
                out.write(black_frame)
            out.release()
            
            # Convert to H.264 format using ffmpeg synchronously
            temp_path = video_path + ".temp.mp4"
            os.rename(video_path, temp_path)
            
            cmd = [
                'ffmpeg',
                '-i', temp_path,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-y',
                video_path
            ]
            
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                if result.returncode != 0:
                    logger.warning(f"Failed to convert video to H.264, using mp4v: {result.stderr.decode()}")
                    # If conversion fails, use the original mp4v version
                    os.rename(temp_path, video_path)
                else:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            except Exception as e:
                logger.warning(f"FFmpeg conversion failed: {e}, using mp4v format")
                # Restore original file if conversion fails
                if os.path.exists(temp_path):
                    os.rename(temp_path, video_path)
        else:
            # 其他图层类型创建png文件
            layer_file_path = os.path.join(layers_path, f"{new_id}.png")
            layer = Layer(new_id, f"Layer-{new_id}", layer_type, True, False,0,0,720,1280,self.timeline_item, self)
            # Create a placeholder png file with 720x1280 dimensions
            img = np.zeros((1280, 720, 4), dtype=np.uint8)  # 720x1280 with alpha
            img[:, :] = [0, 0, 0, 0]  # Transparent black
            cv2.imwrite(layer_file_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            
            # 设置图层的默认尺寸
            layer.width = 720
            layer.height = 1280
        
        return self._add_layer(layer)

    def add_layer_from_file(self, source_path: str, layer_type: LayerType = LayerType.IMAGE) -> Layer:
        # 检查timeline_item是否已加载
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # 生成新的图层ID（基于现有最大ID+1，避免删除后的ID冲突）
        if self.layers:
            existing_ids = list(self.layers.keys())
            new_id = max(existing_ids) + 1
        else:
            new_id = 1

        # 获取源文件扩展名
        ext = os.path.splitext(source_path)[1] or ".png"
        layer_file_path = os.path.join(self.timeline_item.layers_path, f"{new_id}{ext}")

        # 复制源文件到layers目录
        shutil.copy2(source_path, layer_file_path)

        # 创建图层对象
        layer = Layer(new_id, f"Layer-{new_id}", layer_type, True, False, 0, 0, 0, 0, self.timeline_item, self)

        # 获取图片尺寸
        if layer_type == LayerType.IMAGE:
            try:
                img = cv2.imread(source_path)
                if img is not None:
                    height, width = img.shape[:2]
                    layer.width = width
                    layer.height = height
                else:
                    layer.width, layer.height = 720, 1280  # 默认尺寸
            except Exception as e:
                logger.error(f"Error reading image dimensions: {e}")
                layer.width, layer.height = 720, 1280  # 默认尺寸
        elif layer_type == LayerType.VIDEO:
            # 获取视频尺寸
            try:
                cap = cv2.VideoCapture(source_path)
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    layer.width = width
                    layer.height = height
                    cap.release()
                else:
                    layer.width, layer.height = 720, 1280  # 默认尺寸
            except Exception as e:
                logger.error(f"Error reading video dimensions: {e}")
                layer.width, layer.height = 720, 1280  # 默认尺寸
        else:
            # 对于非图片/视频类型，使用默认尺寸
            layer.width, layer.height = 720, 1280  # 默认尺寸

        return self._add_layer(layer)

    def _add_layer(self, layer: Layer) -> Layer:
        # 使用字典存储图层
        self.layers[layer.id] = layer
        self._save_layers()
        # Emit the general layer_changed signal only if the current timeline_item 
        # in this layer manager is the currently selected timeline_item
        if self.timeline_item:
            current_item = self.timeline_item.timeline.get_current_item()
            if current_item and self.timeline_item.index == current_item.index:
                self.layer_changed.send(self, layer=layer, change_type='added')
        return layer

    def remove_layer(self, layer_id: int) -> bool:
        # 检查timeline_item是否已加载
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # 直接通过ID访问图层
        if layer_id in self.layers:
            layer = self.layers[layer_id]
            # 先删除对应的文件
            layers_path = self.timeline_item.layers_path
            # Find all files that start with the layer ID followed by a dot (e.g., "1.png", "1.mp4", etc.)
            layer_files = []
            if os.path.exists(layers_path):
                for file_name in os.listdir(layers_path):
                    if file_name.startswith(f"{layer_id}."):
                        layer_files.append(os.path.join(layers_path, file_name))
            
            # Remove the found files
            for file_path in layer_files:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted layer file: {file_path}")
                except OSError as e:
                    logger.error(f"Error deleting layer file {file_path}: {e}")
            
            # 从内存和配置中删除图层
            del self.layers[layer_id]
            self._save_layers()

            # Emit the general layer_changed signal only if the current timeline_item
            # in this layer manager is the currently selected timeline_item
            current_item = self.timeline_item.timeline.get_current_item()
            if current_item and self.timeline_item.index == current_item.index:
                self.layer_changed.send(self, layer=layer, change_type='removed')
            
            return True
        return False

    def toggle_visibility(self, layer_id: int) -> Optional[bool]:
        # 检查timeline_item是否已加载
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # 直接通过ID访问图层
        if layer_id in self.layers:
            layer = self.layers[layer_id]
            layer.visible = not layer.visible
            self._save_layers()
            # Emit the general layer_changed signal only if the current timeline_item
            # in this layer manager is the currently selected timeline_item
            current_item = self.timeline_item.timeline.get_current_item()
            if current_item and self.timeline_item.index == current_item.index:
                self.layer_changed.send(self, layer=layer, change_type='modified')

            return layer.visible
        return None

    def toggle_lock(self, layer_id: int) -> Optional[bool]:
        # 检查timeline_item是否已加载
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # 直接通过ID访问图层
        if layer_id in self.layers:
            layer = self.layers[layer_id]
            layer.locked = not layer.locked
            self._save_layers()
            # Emit the general layer_changed signal only if the current timeline_item
            # in this layer manager is the currently selected timeline_item
            current_item = self.timeline_item.timeline.get_current_item()
            if current_item and self.timeline_item.index == current_item.index:
                self.layer_changed.send(self, layer=layer, change_type='modified')

            return layer.locked
        return None

    def rename_layer(self, layer_id: int, new_name: str) -> bool:
        # 检查timeline_item是否已加载
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # 直接通过ID访问图层
        if layer_id in self.layers:
            layer = self.layers[layer_id]
            layer.name = new_name
            self._save_layers()
            # Emit the general layer_changed signal only if the current timeline_item 
            # in this layer manager is the currently selected timeline_item
            if self.timeline_item.index == self.timeline_item.timeline.get_current_item().index:
                self.layer_changed.send(self, layer=layer, change_type='modified')
            
            return True
        return False

    def move_layer(self, layer_id: int, new_position: int) -> bool:
        # 检查timeline_item是否已加载
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # 获取按ID排序的图层列表
        sorted_layer_ids = sorted(self.layers.keys())
        if new_position < 0 or new_position >= len(sorted_layer_ids):
            return False

        # 找到要移动的图层
        if layer_id not in self.layers:
            return False

        # 移动图层（在保存时调整顺序）
        self._save_layers()
        # Emit the general layer_changed signal only if the current timeline_item
        # in this layer manager is the currently selected timeline_item
        current_item = self.timeline_item.timeline.get_current_item()
        if current_item and self.timeline_item.index == current_item.index:
            layer_obj = self.layers[layer_id]
            self.layer_changed.send(self, layer=layer_obj, change_type='reordered')
        
        return True

    def get_layer(self, layer_id: int) -> Optional[Layer]:
        # 直接通过ID访问图层
        return self.layers.get(layer_id)

    def get_layers(self):
        # 按ID排序返回图层列表
        result = [self.layers[layer_id] for layer_id in sorted(self.layers.keys())] if self.layers is not None else []
        return result

    def composite_visible_layers(self, layer_image_paths: List[Tuple[Layer, str]], output_path: str,
                                 canvas_size: Tuple[int, int] = (1920, 1080)):
        """
        将多个可见图层的图片绘制到一个图片文件中

        Args:
            layer_image_paths: 包含图层和图像路径的元组列表 [(layer, image_path), ...]
            output_path: 输出图像文件路径
            canvas_size: 画布尺寸 (width, height)
        """
        # 创建一个透明背景的画布 (RGBA)
        canvas = np.zeros((canvas_size[1], canvas_size[0], 4), dtype=np.uint8)
        # Set alpha channel to 0 (fully transparent)
        canvas[:, :, 3] = 0

        # 按照图层顺序从下到上绘制图层
        for layer, image_path in layer_image_paths:
            if not os.path.exists(image_path):
                continue

            # 跳过不可见图层
            if not layer.visible:
                continue

            # 读取图层图像
            layer_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if layer_image is None:
                continue

            # Ensure image has 4 channels (RGBA)
            if len(layer_image.shape) == 2:
                # Grayscale - convert to RGBA
                layer_image = cv2.cvtColor(layer_image, cv2.COLOR_GRAY2BGR)
                alpha = np.ones((layer_image.shape[0], layer_image.shape[1], 1), dtype=np.uint8) * 255
                layer_image = np.concatenate([layer_image, alpha], axis=2)
            elif layer_image.shape[2] == 3:
                # RGB - add alpha channel (fully opaque)
                alpha = np.ones((layer_image.shape[0], layer_image.shape[1], 1), dtype=np.uint8) * 255
                layer_image = np.concatenate([layer_image, alpha], axis=2)
            elif layer_image.shape[2] == 4:
                # Already RGBA
                pass

            # 调整图层图像大小以匹配图层指定的尺寸
            if layer.width > 0 and layer.height > 0:
                layer_image = cv2.resize(layer_image, (layer.width, layer.height))
            else:
                layer.height, layer.width = layer_image.shape[:2]

            # 确保图层在画布范围内
            if (0 <= layer.x < canvas_size[0] and 0 <= layer.y < canvas_size[1] and
                    layer.x + layer.width <= canvas_size[0] and layer.y + layer.height <= canvas_size[1] and
                    layer.width > 0 and layer.height > 0):

                # 提取RGBA通道
                b, g, r, a = cv2.split(layer_image)
                layer_rgb = cv2.merge([b, g, r])
                alpha = a.astype(float) / 255.0

                # 提取画布上对应区域
                canvas_region = canvas[layer.y:layer.y + layer.height, layer.x:layer.x + layer.width]
                canvas_b, canvas_g, canvas_r, canvas_a = cv2.split(canvas_region)
                canvas_rgb = cv2.merge([canvas_b, canvas_g, canvas_r])
                canvas_alpha = canvas_a.astype(float) / 255.0

                # Alpha compositing: result = foreground * alpha_fg + background * alpha_bg * (1 - alpha_fg)
                # New alpha: alpha_out = alpha_fg + alpha_bg * (1 - alpha_fg)
                alpha_out = alpha + canvas_alpha * (1 - alpha)
                
                # Avoid division by zero
                alpha_out_safe = np.where(alpha_out > 0, alpha_out, 1)
                
                # Composite RGB channels
                for c in range(3):
                    if c == 0:
                        fg = layer_rgb[:, :, c].astype(float)
                        bg = canvas_rgb[:, :, c].astype(float)
                    elif c == 1:
                        fg = layer_rgb[:, :, c].astype(float)
                        bg = canvas_rgb[:, :, c].astype(float)
                    else:
                        fg = layer_rgb[:, :, c].astype(float)
                        bg = canvas_rgb[:, :, c].astype(float)
                    
                    # Composite: (fg * alpha_fg + bg * alpha_bg * (1 - alpha_fg)) / alpha_out
                    composite = (fg * alpha + bg * canvas_alpha * (1 - alpha)) / alpha_out_safe
                    canvas_region[:, :, c] = composite.astype(np.uint8)
                
                # Set output alpha
                canvas_region[:, :, 3] = (alpha_out * 255).astype(np.uint8)
                
                canvas[layer.y:layer.y + layer.height, layer.x:layer.x + layer.width] = canvas_region

        # 保存最终合成的图像 (with alpha channel)
        cv2.imwrite(output_path, canvas, [cv2.IMWRITE_PNG_COMPRESSION, 9])

    async def compose_layers(self) -> str:
        """
        Compose visible layers into image.png and video.mp4.
        This is a heavy operation that is queued to avoid blocking the main thread.
        Only one composition task per LayerManager can run at a time.
        
        This method is automatically called when layers change if auto_compose is enabled.
        It can also be called manually when needed.
        
        Returns:
            str: Task ID for tracking the composition task
        """
        if self.timeline_item is None:
            raise ValueError("LayerManager has not loaded timeline_item yet. Call load_layers() first.")
        
        # Submit task to the global composition task manager
        task_manager = get_compose_task_manager()
        task_id = await task_manager.submit_compose_task(self)

        logger.info(f"Layer composition task {task_id} submitted for timeline item {self.timeline_item.index}")
        return task_id


class LayerComposeTask:
    """Layer composition task"""
    
    def __init__(self, layer_manager: 'LayerManager', task_id: str):
        self.layer_manager = layer_manager
        self.task_id = task_id
        self.output_dir = layer_manager.timeline_item.get_item_path()
        self.output_png = os.path.join(self.output_dir, "image.png")
        self.output_mp4 = os.path.join(self.output_dir, "video.mp4")
    
    async def execute(self):
        """Execute the composition task"""
        try:
            logger.info(f"Starting layer composition task {self.task_id} for timeline item {self.layer_manager.timeline_item.index}")
            logger.debug(f"Thread info: {threading.current_thread().name} (ID: {threading.get_ident()})")
            
            # Get visible layers from top to bottom
            all_layers = self.layer_manager.get_layers()
            if not all_layers:
                logger.warning("No layers to compose")
                return
            
            # Reverse to get top-to-bottom order
            top_to_bottom_layers = list(reversed(all_layers))
            
            # Find visible layers to compose (stop at first video layer)
            layers_to_compose = []
            has_video = False
            
            for layer in top_to_bottom_layers:
                if not layer.visible:
                    continue
                
                # Check if layer file exists before adding to composition list
                layer_path = layer.get_layer_path()
                if not layer_path or not os.path.exists(layer_path):
                    logger.warning(f"Layer {layer.id} file not found: {layer_path}, skipping")
                    continue
                
                layers_to_compose.append(layer)
                
                # Stop at video layer (videos are not transparent)
                if layer.type == LayerType.VIDEO:
                    has_video = True
                    break
            
            if not layers_to_compose:
                logger.warning("No visible layers to compose")
                return
            
            # Reverse to get bottom-to-top order for composition
            layers_to_compose.reverse()
            
            logger.info(f"Composing {len(layers_to_compose)} layers (has_video: {has_video})")
            
            # Perform composition based on layer types
            if has_video:
                await self._compose_with_video(layers_to_compose)
            else:
                await self._compose_images_only(layers_to_compose)
            
            logger.info(f"Layer composition task {self.task_id} completed successfully")
            
            # Fire timeline_changed signal after composition completes and image.png is created
            self._fire_timeline_changed_signal()
            
        except Exception as e:
            # Log the error but don't re-raise to prevent thread crashes
            logger.error(f"Error in layer composition task {self.task_id}: {e}", exc_info=True)
            logger.error(f"Thread info: {threading.current_thread().name} (ID: {threading.get_ident()})")
            # Attempt to create placeholder outputs if they don't exist
            try:
                self._create_placeholder_outputs()
            except Exception as fallback_error:
                logger.error(f"Failed to create placeholder outputs: {fallback_error}")
    
    def _create_placeholder_outputs(self):
        """Create placeholder output files if composition failed"""
        import cv2
        import numpy as np
        
        # Create placeholder image if it doesn't exist
        if not os.path.exists(self.output_png):
            try:
                placeholder_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
                cv2.imwrite(self.output_png, placeholder_img)
                logger.info(f"Created placeholder image: {self.output_png}")
            except Exception as e:
                logger.error(f"Failed to create placeholder image: {e}")
        
        # Create placeholder video if it doesn't exist
        if not os.path.exists(self.output_mp4):
            try:
                # Create a 1-second black video
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(self.output_mp4, fourcc, 8.0, (1920, 1080))
                black_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                for _ in range(8):  # 8 frames at 8fps = 1 second
                    out.write(black_frame)
                out.release()
                logger.info(f"Created placeholder video: {self.output_mp4}")
            except Exception as e:
                logger.error(f"Failed to create placeholder video: {e}")
    
    async def _compose_images_only(self, layers: List['Layer']):
        """Compose image layers only - convert to 1 second 8fps video"""
        # Determine canvas size from layers
        max_width = 0
        max_height = 0
        for layer in layers:
            if layer.width > 0 and layer.height > 0:
                layer_right = layer.x + layer.width
                layer_bottom = layer.y + layer.height
                max_width = max(max_width, layer_right)
                max_height = max(max_height, layer_bottom)
        
        # Use a minimum canvas size if no valid layer dimensions found
        canvas_width = max(max_width, 720) if max_width > 0 else 1920
        canvas_height = max(max_height, 1280) if max_height > 0 else 1080
        canvas_size = (canvas_width, canvas_height)
        
        logger.info(f"Canvas size for image composition: {canvas_size}")
        
        temp_composite = os.path.join(self.output_dir, "_temp_composite.png")
        
        # Use existing composite_visible_layers method
        layer_path_tuples = []
        for layer in layers:
            layer_path = layer.get_layer_path()
            if layer_path and os.path.exists(layer_path):
                layer_path_tuples.append((layer, layer_path))
            else:
                logger.warning(f"Image layer {layer.id} file not found: {layer_path}, skipping")
        
        if not layer_path_tuples:
            logger.warning("No valid image layers to compose")
            return
        
        self.layer_manager.composite_visible_layers(
            layer_path_tuples, 
            temp_composite, 
            canvas_size
        )
        
        # Save the composite image as output.png (with alpha channel)
        import shutil
        shutil.copy2(temp_composite, self.output_png)
        
        # Convert image to 8fps 1-second video
        from utils.ffmpeg_utils import run_command
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', temp_composite,
            '-c:v', 'libx264',
            '-t', '1',  # 1 second duration
            '-r', '8',  # 8 fps
            '-pix_fmt', 'yuv420p',
            '-y',
            self.output_mp4
        ]
        
        result = await run_command(cmd)
        if result.returncode != 0:
            logger.error(f"Failed to create video from images: {result.stderr.decode()}")
            raise RuntimeError("Failed to create video from images")
        
        # Clean up temp file
        if os.path.exists(temp_composite):
            os.remove(temp_composite)
    
    async def _compose_with_video(self, layers: List['Layer']):
        """Compose layers with video - overlay images on video frames"""
        # Find the video layer (should be the bottom one after reversing)
        video_layer = None
        image_layers = []
        
        for layer in layers:
            if layer.type == LayerType.VIDEO:
                video_layer = layer
            elif layer.type == LayerType.IMAGE:
                image_layers.append(layer)
        
        if not video_layer:
            logger.warning("No video layer found, falling back to image composition")
            await self._compose_images_only(layers)
            return
        
        video_path = video_layer.get_layer_path()
        if not video_path or not os.path.exists(video_path):
            logger.warning(f"Video layer file not found: {video_path}, falling back to image composition")
            await self._compose_images_only([l for l in layers if l.type == LayerType.IMAGE])
            return
        
        # Get video properties - validate video file
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning(f"Failed to open video: {video_path}, falling back to image composition")
            cap.release()
            await self._compose_images_only([l for l in layers if l.type == LayerType.IMAGE])
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        # Validate video properties
        if fps <= 0 or width <= 0 or height <= 0 or frame_count <= 0:
            logger.warning(f"Invalid video properties (fps={fps}, size={width}x{height}, frames={frame_count}), falling back to image composition")
            await self._compose_images_only([l for l in layers if l.type == LayerType.IMAGE])
            return
        
        logger.info(f"Video properties: {width}x{height}, {fps}fps, {frame_count} frames")
        
        # If no image layers, just copy the video
        if not image_layers:
            import shutil
            shutil.copy2(video_path, self.output_mp4)
            await self._extract_first_frame()
            return
        
        # Prepare overlay images with alpha channel
        overlay_data = []
        for img_layer in image_layers:
            img_path = img_layer.get_layer_path()
            if not img_path or not os.path.exists(img_path):
                continue
            
            # Read image with alpha channel
            img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                continue
            
            # Ensure image has alpha channel
            if img.shape[2] == 3:
                # Add alpha channel (fully opaque)
                alpha = np.ones((img.shape[0], img.shape[1], 1), dtype=img.dtype) * 255
                img = np.concatenate([img, alpha], axis=2)
            
            # Resize if needed
            if img_layer.width > 0 and img_layer.height > 0:
                img = cv2.resize(img, (img_layer.width, img_layer.height))
            
            overlay_data.append({
                'image': img,
                'x': img_layer.x,
                'y': img_layer.y,
                'width': img_layer.width if img_layer.width > 0 else img.shape[1],
                'height': img_layer.height if img_layer.height > 0 else img.shape[0]
            })
        
        # Process video frame by frame
        temp_output = os.path.join(self.output_dir, "_temp_output.mp4")
        
        # Open video for reading
        cap = cv2.VideoCapture(video_path)
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
        
        if not out.isOpened():
            logger.warning("VideoWriter failed to open, using ffmpeg overlay instead")
            cap.release()
            out.release()
            # Fall back to ffmpeg-based composition
            await self._compose_with_video_ffmpeg(video_path, image_layers, width, height)
            return
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Overlay each image layer on the frame
            for overlay in overlay_data:
                img = overlay['image']
                x, y = overlay['x'], overlay['y']
                w, h = overlay['width'], overlay['height']
                
                # Ensure overlay is within frame bounds
                if x < 0 or y < 0 or x + w > width or y + h > height:
                    continue
                
                # Extract alpha channel
                if img.shape[2] == 4:
                    b, g, r, a = cv2.split(img)
                    overlay_rgb = cv2.merge([b, g, r])
                    alpha = a.astype(float) / 255.0
                    
                    # Get region of interest
                    roi = frame[y:y+h, x:x+w]
                    
                    # Blend with alpha
                    for c in range(3):
                        roi[:, :, c] = (1 - alpha) * roi[:, :, c] + alpha * overlay_rgb[:, :, c]
                    
                    frame[y:y+h, x:x+w] = roi
                else:
                    # No alpha, direct copy
                    frame[y:y+h, x:x+w] = img
            
            out.write(frame)
            frame_idx += 1
        
        cap.release()
        out.release()
        
        # Convert to proper H.264 format
        from utils.ffmpeg_utils import run_command
        
        cmd = [
            'ffmpeg',
            '-i', temp_output,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',
            self.output_mp4
        ]
        
        result = await run_command(cmd)
        if result.returncode != 0:
            logger.error(f"Failed to convert video: {result.stderr.decode()}")
            raise RuntimeError("Failed to convert video")
        
        # Extract first frame as output.png
        await self._extract_first_frame()
        
        # Clean up temp file
        if os.path.exists(temp_output):
            os.remove(temp_output)
    
    async def _compose_with_video_ffmpeg(self, video_path: str, image_layers: List['Layer'], width: int, height: int):
        """Compose video with image overlays using FFmpeg directly"""
        from utils.ffmpeg_utils import run_command
        
        if not image_layers:
            # Just copy the video
            import shutil
            shutil.copy2(video_path, self.output_mp4)
            await self._extract_first_frame()
            return
        
        # Filter valid image layers and build inputs
        valid_layers = []
        for img_layer in image_layers:
            img_path = img_layer.get_layer_path()
            if img_path and os.path.exists(img_path):
                valid_layers.append(img_layer)
        
        if not valid_layers:
            # No valid overlays, just copy
            logger.warning("No valid image layers found for overlay, copying video")
            import shutil
            shutil.copy2(video_path, self.output_mp4)
            await self._extract_first_frame()
            return
        
        # Build FFmpeg filter_complex for overlays
        # Start with the video as input [0:v]
        filter_parts = []
        current_stream = '0:v'
        
        for i, img_layer in enumerate(valid_layers):
            overlay_index = i + 1  # Input index in ffmpeg (0 is video, 1+ are images)
            output_stream = f'tmp{i}'
            
            # Position for overlay
            x, y = img_layer.x, img_layer.y
            
            # Create overlay filter
            if i == len(valid_layers) - 1:
                # Last overlay outputs to final stream
                filter_parts.append(f'[{current_stream}][{overlay_index}:v]overlay={x}:{y}[v]')
            else:
                filter_parts.append(f'[{current_stream}][{overlay_index}:v]overlay={x}:{y}[{output_stream}]')
                current_stream = output_stream
        
        # Build command
        cmd = ['ffmpeg', '-i', video_path]
        
        # Add image inputs (only valid ones)
        for img_layer in valid_layers:
            img_path = img_layer.get_layer_path()
            cmd.extend(['-i', img_path])
        
        filter_complex = ';'.join(filter_parts)
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-map', '0:a?',  # Copy audio if present
            '-c:v', 'libx264',
            '-c:a', 'copy',
            '-pix_fmt', 'yuv420p',
            '-y',
            self.output_mp4
        ])
        
        logger.info(f"FFmpeg overlay command: {' '.join(cmd)}")
        
        try:
            result = await run_command(cmd)
            if result.returncode != 0:
                stderr_output = result.stderr.decode() if result.stderr else 'No error output'
                logger.error(f"FFmpeg overlay failed (returncode={result.returncode}): {stderr_output}")
                # Fallback: just copy the video without overlays
                logger.warning("Falling back to copying video without overlays")
                import shutil
                shutil.copy2(video_path, self.output_mp4)
                await self._extract_first_frame()
                return
        except Exception as e:
            logger.error(f"Exception during FFmpeg overlay: {e}", exc_info=True)
            # Fallback: just copy the video
            logger.warning("Falling back to copying video without overlays due to exception")
            import shutil
            shutil.copy2(video_path, self.output_mp4)
            await self._extract_first_frame()
            return
        
        # Extract first frame
        await self._extract_first_frame()
    
    async def _extract_first_frame(self):
        """Extract first frame from output.mp4 as output.png"""
        from utils.ffmpeg_utils import run_command
        
        # Check if output video exists
        if not os.path.exists(self.output_mp4):
            logger.error(f"Cannot extract frame: {self.output_mp4} does not exist")
            return
        
        cmd = [
            'ffmpeg',
            '-i', self.output_mp4,
            '-vframes', '1',
            '-y',
            self.output_png
        ]
        
        try:
            result = await run_command(cmd)
            if result.returncode != 0:
                stderr_output = result.stderr.decode() if result.stderr else 'No error output'
                logger.error(f"Failed to extract first frame (returncode={result.returncode}): {stderr_output}")
                # Try to create a placeholder image if extraction fails
                try:
                    import cv2
                    import numpy as np
                    # Create a black placeholder image
                    placeholder = np.zeros((1080, 1920, 3), dtype=np.uint8)
                    cv2.imwrite(self.output_png, placeholder)
                    logger.warning(f"Created placeholder image at {self.output_png}")
                except Exception as e:
                    logger.error(f"Failed to create placeholder image: {e}")
        except Exception as e:
            logger.error(f"Exception during frame extraction: {e}", exc_info=True)
    
    def _fire_timeline_changed_signal(self):
        """Fire timeline_changed signal when composition completes"""
        try:
            timeline_item = self.layer_manager.timeline_item
            if timeline_item and hasattr(timeline_item, 'timeline'):
                timeline = timeline_item.timeline
                if hasattr(timeline, 'timeline_changed'):
                    # Send signal with timeline_item as parameter
                    timeline.timeline_changed.send(timeline, timeline_item=timeline_item)
                    logger.info(f"Fired timeline_changed signal for timeline item {timeline_item.index}")
        except Exception as e:
            logger.warning(f"Failed to fire timeline_changed signal: {e}")


class LayerComposeTaskManager:
    """Manages layer composition tasks with queueing.
    
    Uses a single background worker thread to execute heavy composition tasks
    sequentially without blocking the UI main thread.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._task_queue = []  # Queue of pending tasks
            self._current_worker = None  # Single active BackgroundWorker
            self._task_counter = 0
            self._initialized = True
            self._shutdown = False  # Flag to indicate shutdown in progress
    
    def _get_layer_manager_id(self, layer_manager: 'LayerManager') -> str:
        """Get unique ID for layer manager"""
        if layer_manager.timeline_item:
            return f"timeline_{layer_manager.timeline_item.index}"
        return str(id(layer_manager))
    
    async def submit_compose_task(self, layer_manager: 'LayerManager') -> str:
        """Submit a composition task for a layer manager.
        
        The task will be executed in a background thread to avoid blocking the UI.
        Tasks are processed sequentially by a single worker.
        """
        # Don't accept new tasks if shutting down
        if hasattr(self, '_shutdown') and self._shutdown:
            logger.warning("Cannot submit task: LayerComposeTaskManager is shutting down")
            return None
        
        manager_id = self._get_layer_manager_id(layer_manager)
        
        # Generate task ID
        self._task_counter += 1
        task_id = f"compose_{self._task_counter}"
        
        # Log submission details
        logger.info(f"Task submission: {task_id} for {manager_id}")
        logger.debug(f"  Current thread: {threading.current_thread().name}")
        logger.debug(f"  Queue size before: {len(self._task_queue)}")
        logger.debug(f"  Current worker running: {self._current_worker.is_running() if self._current_worker else False}")
        
        # Create task
        task = LayerComposeTask(layer_manager, task_id)
        task.manager_id = manager_id  # Store manager_id on task
        
        # Remove any existing pending tasks for the same manager_id (only latest matters)
        old_queue_size = len(self._task_queue)
        self._task_queue = [t for t in self._task_queue if t.manager_id != manager_id]
        replaced_count = old_queue_size - len(self._task_queue)
        if replaced_count > 0:
            logger.info(f"Replaced {replaced_count} pending task(s) for {manager_id}")
        
        # Add new task to queue
        self._task_queue.append(task)
        logger.info(f"Queued composition task {task_id} for {manager_id} (queue size: {len(self._task_queue)})")
        
        # Start processing if no worker is active
        if self._current_worker is None or not self._current_worker.is_running():
            logger.debug(f"Starting task processing (worker inactive)")
            self._process_next_task()
        else:
            logger.debug(f"Worker already running, task will be processed when current task completes")
        
        return task_id
    
    def _process_next_task(self):
        """Process the next task in the queue."""
        if not self._task_queue:
            logger.debug("No tasks in queue to process")
            return
        
        # Safety check: ensure no worker is currently running
        if self._current_worker is not None and self._current_worker.is_running():
            logger.warning("Cannot start next task: current worker still running")
            logger.warning("Rescheduling task processing in 500ms...")
            try:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(500, self._process_next_task)
            except ImportError:
                pass
            return
        
        # Get next task
        task = self._task_queue.pop(0)
        logger.info(f"Starting composition task {task.task_id} for {task.manager_id}")
        logger.debug(f"Remaining tasks in queue: {len(self._task_queue)}")
        
        # Start the task in background
        self._start_qt_background_task(task)

    
    def _start_qt_background_task(self, task: 'LayerComposeTask'):
        """Start a composition task using Qt background worker."""
        from app.ui.worker.worker import run_in_background
        
        def execute_task_sync():
            """Wrapper to run async task in a new event loop within the background thread."""
            import asyncio
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Run the async execute method
                loop.run_until_complete(task.execute())
            finally:
                loop.close()
        
        def on_finished(result):
            """Handle task completion and start next queued task if any."""
            logger.info(f"Composition task {task.task_id} completed for {task.manager_id}")
            self._on_task_finished()
        
        def on_error(error_msg, exception):
            """Handle task error and start next queued task if any."""
            logger.error(f"Composition task {task.task_id} failed: {error_msg}")
            self._on_task_finished()
        
        # Run in background thread
        worker = run_in_background(
            task=execute_task_sync,
            on_finished=on_finished,
            on_error=on_error
        )
        
        # Disable auto-cleanup - we'll manage cleanup ourselves
        worker.set_auto_cleanup(False)
        
        self._current_worker = worker
    
    def _on_task_finished(self):
        """Called when a task finishes. Starts next queued task if any."""
        logger.debug("Task finished callback triggered")
        
        # Clean up current worker with deferred deletion
        self._cleanup_current_worker()
        
        # Don't process next task if shutting down
        if hasattr(self, '_shutdown') and self._shutdown:
            logger.info("Skipping next task due to shutdown")
            return
        
        # Process next task in queue AFTER cleanup completes
        if self._task_queue:
            # Use QTimer to ensure cleanup is complete before starting next task
            # Increased delay from 50ms to 600ms to ensure worker cleanup finishes
            try:
                from PySide6.QtCore import QTimer
                logger.debug(f"Scheduling next task in 600ms (queue size: {len(self._task_queue)})")
                QTimer.singleShot(600, self._process_next_task)
            except ImportError:
                logger.warning("QTimer not available, processing next task immediately")
                self._process_next_task()
        else:
            logger.info("All composition tasks completed")
    
    def _cleanup_current_worker(self):
        """Clean up the current worker with proper thread termination."""
        if self._current_worker is None:
            return
        
        worker = self._current_worker
        self._current_worker = None
        
        logger.debug(f"Starting worker cleanup (running: {worker.is_running() if worker._thread else False})")
        
        # Properly stop the worker thread
        try:
            # First, ensure the thread is stopped
            if worker._thread is not None:
                thread_was_running = worker._thread.isRunning()
                
                if thread_was_running:
                    logger.warning(f"Worker thread still running during cleanup, waiting for completion...")
                    
                # Quit the thread's event loop
                worker._thread.quit()
                
                # Wait for thread to actually finish (with timeout)
                # Increased timeout from 5s to 10s for complex compositions
                if not worker._thread.wait(10000):  # 10 second timeout
                    logger.error("Worker thread did not finish in time, forcing termination")
                    worker._thread.terminate()
                    worker._thread.wait(2000)  # Wait 2 more seconds after terminate
                else:
                    logger.debug(f"Worker thread stopped gracefully (was running: {thread_was_running})")
            
            # Use QTimer to defer the final deletion, allowing all Qt events to process
            from PySide6.QtCore import QTimer
            # Move worker to a temporary list to prevent garbage collection
            if not hasattr(self, '_cleanup_pending'):
                self._cleanup_pending = []
            self._cleanup_pending.append(worker)
            
            def do_cleanup():
                if worker in self._cleanup_pending:
                    self._cleanup_pending.remove(worker)
                    # Explicitly delete the worker's thread and executor
                    if worker._thread is not None:
                        worker._thread.deleteLater()
                        worker._thread = None
                    if worker._executor is not None:
                        worker._executor.deleteLater()
                        worker._executor = None
                    logger.debug("Worker cleanup completed")
            
            # Increased delay from 200ms to 500ms to ensure Qt event processing
            QTimer.singleShot(500, do_cleanup)
        except Exception as e:
            logger.error(f"Error during worker cleanup: {e}", exc_info=True)
    
    def shutdown(self):
        """Shutdown the task manager and clean up all resources.
        
        Should be called when the application is closing.
        """
        logger.info("Shutting down LayerComposeTaskManager")
        self._shutdown = True
        
        # Clear pending tasks
        self._task_queue.clear()
        
        # Clean up current worker
        self._cleanup_current_worker()
        
        # Clean up any pending cleanup workers
        if hasattr(self, '_cleanup_pending'):
            for worker in self._cleanup_pending:
                try:
                    if worker._thread is not None:
                        worker._thread.quit()
                        worker._thread.wait(2000)
                        worker._thread.deleteLater()
                except Exception as e:
                    logger.error(f"Error cleaning up pending worker: {e}")
            self._cleanup_pending.clear()
        
        logger.info("LayerComposeTaskManager shutdown complete")


# Global instance
_compose_task_manager = None

def get_compose_task_manager() -> LayerComposeTaskManager:
    """Get global composition task manager instance"""
    global _compose_task_manager
    if _compose_task_manager is None:
        _compose_task_manager = LayerComposeTaskManager()
    return _compose_task_manager