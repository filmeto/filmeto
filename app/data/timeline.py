import os.path
import shutil
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QPixmap, Qt

from app.data.task import TaskResult, TimelineItemTaskManager
from app.data.layer import LayerManager, LayerType

from blinker import signal

from utils import dict_utils
from utils.yaml_utils import load_yaml, save_yaml

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.project import Project


class TimelineItem:
    """
    Represents a single item in the timeline.
    
    Each timeline item has its own:
    - Image/video content
    - Layer manager
    - Task manager (for task storage)
    - Configuration
    """

    def __init__(self, timeline: 'Timeline', timelinePath: str, index: int, layer_changed_signal=None):
        self.timeline = timeline
        self.time_line_path = timelinePath
        self.index = index
        self.item_path = os.path.join(self.time_line_path, str(self.index))
        self.image_path = os.path.join(self.item_path, "image.png")
        self.video_path = os.path.join(self.item_path, "video.mp4")
        self.config_path = os.path.join(self.item_path, "config.yml")
        self.layers_path = os.path.join(self.item_path, "layers")
        self.tasks_path = os.path.join(self.item_path, "tasks")
        self.config = load_yaml(self.config_path) or {}
        self._layer_changed_signal = layer_changed_signal
        self.layer_manager = None
        self._task_manager: TimelineItemTaskManager = None  # Lazy-loaded
        
        # Create directories if they don't exist
        os.makedirs(self.layers_path, exist_ok=True)
        os.makedirs(self.tasks_path, exist_ok=True)
        
        # Migrate legacy duration from item config to project config
        self._migrate_duration_if_needed()
        
        # Initialize duration if not set in project config
        if not self.timeline.project.has_item_duration(self.index):
            self._initialize_duration()


    def get_image(self):
        original_pixmap= QPixmap(self.image_path)
        return original_pixmap
    
    def _migrate_duration_if_needed(self):
        """Migrate legacy duration from item config to project config"""
        if 'duration' in self.config:
            # Found legacy duration in item config - migrate to project config
            legacy_duration = self.config['duration']
            self.timeline.project.set_item_duration(self.index, legacy_duration)
            # Remove from item config (optional - could keep for backward compatibility)
            # del self.config['duration']
            # save_yaml(self.config_path, self.config)
    
    def _initialize_duration(self):
        """Initialize duration based on item type (image or video)"""
        if os.path.exists(self.video_path):
            # Video item - get duration from video file
            from utils.opencv_utils import get_video_duration
            duration = get_video_duration(self.video_path)
            if duration is not None:
                self.timeline.project.set_item_duration(self.index, duration)
            else:
                # Fallback to default if we can't read video duration
                self.timeline.project.set_item_duration(self.index, 1.0)
        else:
            # Image item - default to 1 second
            self.timeline.project.set_item_duration(self.index, 1.0)
        # Notify timeline to update total duration
        self.timeline._on_item_duration_changed()

    def update_image(self, image_path:str):
        if image_path is None:
            return
        # Always use the TimelineItem's own LayerManager (lazy-loaded)
        layer_manager = self.get_layer_manager()
        # Add the source file as a new IMAGE layer
        layer = layer_manager.add_layer_from_file(image_path, LayerType.IMAGE)

    def update_video(self, video_path:str):
        if video_path is None:
            return
        
        # Copy the video file directly to the timeline item's video path
        shutil.copy2(video_path, self.video_path)
        
        # Get the layer manager and register the video as a new layer
        layer_manager = self.get_layer_manager()
        # Add the video file as a layer (using VIDEO type for video files)
        layer_manager.add_layer_from_file(self.video_path, LayerType.VIDEO)
        
        # Update duration based on the new video
        from utils.opencv_utils import get_video_duration
        duration = get_video_duration(self.video_path)
        if duration is not None:
            self.timeline.project.set_item_duration(self.index, duration)
            # Notify timeline to update total duration
            self.timeline._on_item_duration_changed()

    def update_config(self,config_path:str):
        shutil.copy2(config_path, self.config_path)

    def get_image_path(self):
        return self.image_path

    def get_video_path(self):
        return self.video_path

    def get_layers_path(self):
        return self.layers_path

    def get_item_path(self):
        """Get the timeline item's directory path"""
        return self.item_path

    def get_preview_path(self):
        if os.path.exists(self.video_path):
            return self.video_path
        return self.image_path

    def get_prompt(self, tool_name: str = None):
        if tool_name and tool_name in self.config:
            # Try to get prompt from tool-specific section
            tool_section = self.config.get(tool_name, {})
            return dict_utils.get_value(tool_section, 'prompt')
        
        # Fall back to the general prompt if tool-specific prompt doesn't exist
        return dict_utils.get_value(self.config, 'prompt')
    
    def set_prompt(self, prompt: str, tool_name: str = None):
        if tool_name:
            # Initialize the tool section if it doesn't exist
            if tool_name not in self.config:
                self.config[tool_name] = {}
            
            # Store in the tool-specific section
            dict_utils.set_value(self.config[tool_name], 'prompt', prompt)
        else:
            # Store as general prompt (in root level)
            dict_utils.set_value(self.config, 'prompt', prompt)
        
        # Also update the config file
        from utils.yaml_utils import save_yaml
        save_yaml(self.config_path, self.config)
    
    def get_tool_config(self, tool_name: str) -> dict:
        return self.config.get(tool_name, {})
    
    def set_tool_config(self, tool_name: str, config_data: dict):
        self.config[tool_name] = config_data or {}
        # Update the config file
        save_yaml(self.config_path, self.config)

    def get_index(self):
        return self.index

    def get_config(self):
        return self.config

    def set_config_value(self,config_key:str,configy_value):
        self.config[config_key] = configy_value
        save_yaml(self.config_path, self.config)

    def get_config_value(self,config_key:str):
        return self.config.get(config_key, None)

    def get_layer_manager(self):
        if self.layer_manager is None:
            self.layer_manager = LayerManager(self._layer_changed_signal)
            self.layer_manager.load_layers(self)
        return self.layer_manager

    def get_task_manager(self) -> TimelineItemTaskManager:
        """Get the TimelineItemTaskManager for this timeline item (lazy-loaded)"""
        if self._task_manager is None:
            self._task_manager = TimelineItemTaskManager(self, self.tasks_path)
            self._task_manager.load_all_tasks()
        return self._task_manager

    def get_tasks_path(self) -> str:
        """Get the path to the tasks directory for this timeline item"""
        return self.tasks_path

    def update_by_task_result(self, result):
        self.update_image(result.get_image_path())
        self.update_video(result.get_video_path())

        # Load the task config
        task_config_path = result.get_task().get_config_path()
        from utils.yaml_utils import load_yaml, save_yaml

        # Load the task configuration data
        task_config_data = load_yaml(task_config_path) or {}

        # Get the tool name
        tool_name = result.get_task().tool

        if tool_name:
            # Get the current timeline item config
            current_timeline_config = load_yaml(self.config_path) or {}

            # Add/Update the tool-specific section with the full task config data
            current_timeline_config[tool_name] = task_config_data

            # Save the updated config back to the timeline item config file
            save_yaml(self.config_path, current_timeline_config)
        else:
            # If no tool name, just update normally
            self.update_config(result.get_task().get_config_path())


class Timeline:

    timeline_switch = signal("timeline_switch")
    layer_changed = signal("layer_changed")
    timeline_changed = signal("timeline_changed")

    def __init__(self, workspace, project, timelinePath:str):
        self.workspace = workspace
        self.project = project
        self.time_line_path = timelinePath
        self._item_cache = {}  # Cache for TimelineItem instances to prevent duplicate signal connections
        try:
            p = Path(self.time_line_path)
            if not p.exists():
                logger.warning(f"路径 '{self.time_line_path}' 不存在。")
                return
            if not p.is_dir():
                logger.warning(f"路径 '{self.time_line_path}' 不是一个目录。")
                return
            directories = [item.name for item in p.iterdir() if item.is_dir()]
            self.item_count = len(directories)
        except PermissionError:
            logger.error(f"没有权限访问路径 '{self.time_line_path}'。")
            return
        except Exception as e:
            logger.error(f"发生错误: {e}")
            return
    
    def _on_item_duration_changed(self):
        """Called when any timeline item's duration changes - updates total timeline duration"""
        self._update_timeline_duration()
    
    def _update_timeline_duration(self):
        """Calculate and update the total timeline duration in project config"""
        total_duration = self.calculate_total_duration()
        self.project.set_timeline_duration(total_duration)
    
    def calculate_total_duration(self) -> float:
        """Calculate the total duration of all timeline items (optimized)"""
        return self.project.calculate_timeline_duration()
    
    def get_total_duration(self) -> float:
        """Get the total timeline duration (calculates on demand)"""
        return self.calculate_total_duration()

    def connect_timeline_switch(self,func):
        self.timeline_switch.connect(func)

    def connect_layer_changed(self, func):
        self.layer_changed.connect(func)
    
    def connect_timeline_changed(self, func):
        """Connect to timeline_changed signal (fired when timeline item composition completes)"""
        self.timeline_changed.connect(func)

    def get_item_count(self):
        return self.item_count

    def get_item(self, index:int):
        # Use cached TimelineItem to prevent duplicate LayerManager/signal connections
        if index not in self._item_cache:
            self._item_cache[index] = TimelineItem(self, self.time_line_path, index, self.layer_changed)
        return self._item_cache[index]

    def get_current_item(self):
        """Get the current timeline item (returns None if no valid item exists)"""
        current_index = self.project.get_timeline_index()
        if current_index is None or current_index <= 0:
            return None
        return self.get_item(current_index)

    def get_items(self):
        """Get all timeline items as a list"""
        items = []
        for i in range(1, self.item_count + 1):  # Timeline items start from index 1
            item = self.get_item(i)
            # Only add items that actually exist (have content)
            if os.path.exists(item.get_image_path()) or os.path.exists(item.get_video_path()):
                items.append(item)
        return items

    def list_items(self) -> dict:
        """
        List all timeline items with comprehensive information.

        Returns:
            A dictionary containing:
            - total_items: Total number of items in the timeline
            - total_duration: Total duration of the timeline in seconds
            - current_index: Currently selected item index (may be 0 if none selected)
            - items: List of item details, each containing:
                - index: Item index (1-indexed)
                - has_image: Whether the item has an image
                - has_video: Whether the item has a video
                - duration: Item duration in seconds
                - preview_path: Path to the preview file (video or image)
                - config: Item configuration dict
                - prompt: Item prompt (if any)
        """
        items_info = []

        for i in range(1, self.item_count + 1):
            item = self.get_item(i)
            has_image = os.path.exists(item.image_path)
            has_video = os.path.exists(item.video_path)

            item_info = {
                "index": i,
                "has_image": has_image,
                "has_video": has_video,
                "duration": self.project.get_item_duration(i) if hasattr(self.project, 'get_item_duration') else None,
                "preview_path": item.get_preview_path(),
                "config": item.get_config() if has_image or has_video else {},
                "item_path": item.get_item_path(),
                "layers_path": item.get_layers_path(),
                "tasks_path": item.get_tasks_path(),
            }

            # Add prompt if available
            prompt = item.get_prompt()
            if prompt:
                item_info["prompt"] = prompt

            items_info.append(item_info)

        return {
            "total_items": self.item_count,
            "total_duration": self.get_total_duration(),
            "current_index": self.project.get_timeline_index() if hasattr(self.project, 'get_timeline_index') else 0,
            "items": items_info,
            "timeline_path": self.time_line_path,
        }


    def on_task_finished(self,result:TaskResult):
        item = self.get_item(result.get_timeline_index())
        item.update_by_task_result(result)
        # Update total timeline duration after task completion
        self._update_timeline_duration()
    
    def refresh_count(self):
        """Refresh the item count by recounting directories"""
        try:
            p = Path(self.time_line_path)
            if not p.exists() or not p.is_dir():
                return
            directories = [item.name for item in p.iterdir() if item.is_dir()]
            self.item_count = len(directories)
        except Exception as e:
            logger.error(f"Error refreshing timeline count: {e}")
    
    def add_item(self):
        """Add a new timeline item and return its index"""
        self.refresh_count()
        new_index = self.item_count + 1
        new_item_path = os.path.join(self.time_line_path, str(new_index))
        os.makedirs(new_item_path, exist_ok=True)
        self.add_image(new_index)
        self.refresh_count()  # Update the count
        # 修复：使用get方法提供默认值，避免KeyError
        num = self.project.config.get('timeline_size', 0)
        self.project.update_config('timeline_size',num+1)
        # 注意：我们不自动更新 timeline_index，它应该保持为用户当前选择的索引
        # Update total timeline duration after adding new item
        self._update_timeline_duration()
        return new_index

    def add_image(self, new_index):
        # Create a default snapshot image file if it doesn't exist
        new_item_path = os.path.join(self.time_line_path, str(new_index))
        default_snapshot_path = os.path.join(new_item_path, "image.png")
        if not os.path.exists(default_snapshot_path):
            # For now, create a blank image - we'll create a simple placeholder
            # by creating a blank QPixmap and saving it
            from PySide6.QtGui import QPixmap, QPainter, QColor
            pixmap = QPixmap(720, 1280)  # Default size
            pixmap.fill(QColor(50, 50, 50))  # Dark gray background
            painter = QPainter(pixmap)
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, f"Card {new_index}")
            painter.end()
            pixmap.save(default_snapshot_path)

    def set_item_index(self, index):
        self.project.update_config('timeline_index', index)
        item = self.get_item(index)
        # Ensure the item's own LayerManager is loaded (lazy-load will handle first-time creation)
        item.get_layer_manager()
        self.timeline_switch.send(item)

    def delete_item(self, index: int) -> bool:
        """
        Delete a timeline item by index.

        Args:
            index: The index of the item to delete (1-indexed)

        Returns:
            True if deletion was successful, False otherwise
        """
        if index < 1 or index > self.item_count:
            logger.warning(f"Invalid index {index} for deletion. Valid range: 1-{self.item_count}")
            return False

        item_path = os.path.join(self.time_line_path, str(index))
        try:
            # Remove the item directory
            if os.path.exists(item_path):
                shutil.rmtree(item_path)

            # Remove from cache
            if index in self._item_cache:
                del self._item_cache[index]

            # Renumber subsequent items to fill the gap
            for i in range(index + 1, self.item_count + 1):
                old_path = os.path.join(self.time_line_path, str(i))
                new_path = os.path.join(self.time_line_path, str(i - 1))
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)

            # Update cache indices for moved items
            new_cache = {}
            for cached_idx, cached_item in self._item_cache.items():
                if cached_idx < index:
                    new_cache[cached_idx] = cached_item
                elif cached_idx > index:
                    # Shift index down by 1
                    cached_item.index = cached_idx - 1
                    cached_item.item_path = os.path.join(self.time_line_path, str(cached_item.index))
                    cached_item.image_path = os.path.join(cached_item.item_path, "image.png")
                    cached_item.video_path = os.path.join(cached_item.item_path, "video.mp4")
                    cached_item.config_path = os.path.join(cached_item.item_path, "config.yml")
                    cached_item.layers_path = os.path.join(cached_item.item_path, "layers")
                    cached_item.tasks_path = os.path.join(cached_item.item_path, "tasks")
                    new_cache[cached_idx - 1] = cached_item
            self._item_cache = new_cache

            # Update the current timeline index if needed
            current_index = self.project.get_timeline_index()
            if current_index == index:
                # If we deleted the current item, switch to the first item or clear selection
                if self.item_count > 1:
                    self.project.update_config('timeline_index', 1)
                else:
                    self.project.update_config('timeline_index', 0)
            elif current_index > index:
                # Shift current index down
                self.project.update_config('timeline_index', current_index - 1)

            # Refresh count and update config
            self.refresh_count()
            num = self.project.config.get('timeline_size', 0)
            self.project.update_config('timeline_size', max(0, num - 1))

            # Update total timeline duration
            self._update_timeline_duration()

            logger.info(f"Deleted timeline item at index {index}")
            return True

        except Exception as e:
            logger.error(f"Error deleting timeline item at index {index}: {e}")
            return False

    def move_item(self, from_index: int, to_index: int) -> bool:
        """
        Move a timeline item from one position to another.

        Args:
            from_index: The current index of the item (1-indexed)
            to_index: The target index for the item (1-indexed)

        Returns:
            True if move was successful, False otherwise
        """
        if from_index < 1 or from_index > self.item_count:
            logger.warning(f"Invalid from_index {from_index}. Valid range: 1-{self.item_count}")
            return False
        if to_index < 1 or to_index > self.item_count:
            logger.warning(f"Invalid to_index {to_index}. Valid range: 1-{self.item_count}")
            return False
        if from_index == to_index:
            return True  # No move needed

        try:
            # Create a temporary directory for the item being moved
            temp_path = os.path.join(self.time_line_path, "_temp_move")
            from_path = os.path.join(self.time_line_path, str(from_index))
            os.rename(from_path, temp_path)

            # Shift items to fill the gap or make space
            if from_index < to_index:
                # Moving forward: shift items from (from_index+1) to to_index down by 1
                for i in range(from_index + 1, to_index + 1):
                    old_path = os.path.join(self.time_line_path, str(i))
                    new_path = os.path.join(self.time_line_path, str(i - 1))
                    if os.path.exists(old_path):
                        os.rename(old_path, new_path)
            else:
                # Moving backward: shift items from to_index to (from_index-1) up by 1
                for i in range(from_index - 1, to_index - 1, -1):
                    old_path = os.path.join(self.time_line_path, str(i))
                    new_path = os.path.join(self.time_line_path, str(i + 1))
                    if os.path.exists(old_path):
                        os.rename(old_path, new_path)

            # Move the item from temp to its final position
            final_path = os.path.join(self.time_line_path, str(to_index))
            os.rename(temp_path, final_path)

            # Clear and rebuild cache
            self._item_cache.clear()

            # Update the current timeline index if needed
            current_index = self.project.get_timeline_index()
            if current_index == from_index:
                self.project.update_config('timeline_index', to_index)
            elif from_index < current_index <= to_index:
                self.project.update_config('timeline_index', current_index - 1)
            elif to_index <= current_index < from_index:
                self.project.update_config('timeline_index', current_index + 1)

            logger.info(f"Moved timeline item from index {from_index} to {to_index}")
            return True

        except Exception as e:
            logger.error(f"Error moving timeline item from {from_index} to {to_index}: {e}")
            return False

    def update_item_content(self, index: int, image_path: str = None, video_path: str = None) -> bool:
        """
        Update the content of a timeline item.

        Args:
            index: The index of the item to update (1-indexed)
            image_path: Optional path to a new image file
            video_path: Optional path to a new video file

        Returns:
            True if update was successful, False otherwise
        """
        if index < 1 or index > self.item_count:
            logger.warning(f"Invalid index {index} for update. Valid range: 1-{self.item_count}")
            return False

        try:
            item = self.get_item(index)

            if image_path and os.path.exists(image_path):
                item.update_image(image_path)

            if video_path and os.path.exists(video_path):
                item.update_video(video_path)

            # Emit timeline_changed signal to refresh UI
            self.timeline_changed.send(self, item)

            logger.info(f"Updated timeline item at index {index}")
            return True

        except Exception as e:
            logger.error(f"Error updating timeline item at index {index}: {e}")
            return False