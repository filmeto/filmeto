# enhanced_task_item_widget.py
import logging
import math
import os
from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QTextEdit, QFrame
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QTime
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QMovie, QPainterPath, QBrush
from utils.i18n_utils import tr
from utils.yaml_utils import load_yaml
from app.ui.workers.async_data_loader import AsyncDataLoaderMixin

logger = logging.getLogger(__name__)

# Thumbnail async reload: debounce coalesces rapid progress updates; tweak here if needed.
THUMBNAIL_RELOAD_DEBOUNCE_MS = 320
THUMBNAIL_LOADING_ANIM_INTERVAL_MS = 50


def _resolve_task_thumbnail_path(
    config_path: str, project_path: Optional[str], task_path: Optional[str]
) -> Optional[str]:
    """
    Resolve absolute path to an image/video file for task thumbnail (background-thread safe).
    Mirrors previous paintEvent logic without Qt types.
    """
    result_path = None
    try:
        task_config = load_yaml(config_path) or {}
        resources = task_config.get("resources", [])
        if resources:
            for resource_info in resources:
                resource_type = resource_info.get("type", "")
                resource_rel = resource_info.get("resource_path", "")
                if resource_rel and project_path:
                    absolute_path = os.path.join(project_path, resource_rel)
                    if os.path.exists(absolute_path):
                        if resource_type == "image" or (
                            resource_type == "video" and result_path is None
                        ):
                            result_path = absolute_path
                            if resource_type == "image":
                                break
        else:
            image_path = task_config.get("image_resource_path", "")
            video_path = task_config.get("video_resource_path", "")
            if image_path and project_path:
                absolute_path = os.path.join(project_path, image_path)
                if os.path.exists(absolute_path):
                    result_path = absolute_path
            elif video_path and project_path:
                absolute_path = os.path.join(project_path, video_path)
                if os.path.exists(absolute_path):
                    result_path = absolute_path

        if not result_path and task_path and os.path.isdir(task_path):
            for filename in os.listdir(task_path):
                if filename.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi", ".mov", ".webm")
                ):
                    result_path = os.path.join(task_path, filename)
                    break
    except Exception as e:
        logger.error(f"Error resolving thumbnail path for {config_path}: {e}")
        if task_path and os.path.isdir(task_path):
            try:
                for filename in os.listdir(task_path):
                    if filename.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi", ".mov", ".webm")
                    ):
                        result_path = os.path.join(task_path, filename)
                        break
            except Exception as scan_err:
                logger.error(f"Error scanning task dir {task_path}: {scan_err}")

    if result_path and os.path.exists(result_path):
        return result_path
    return None


class EnhancedTaskItemWidget(QWidget, AsyncDataLoaderMixin):
    clicked = Signal(object)  # Signal emitted when task item is clicked

    def __init__(self, task, workspace=None, parent=None):
        super().__init__(parent)
        self.task_id = task.task_id
        self.task = task
        self.is_selected = False
        self.status_animation = None
        self.workspace = workspace
        self._thumbnail_pixmap: Optional[QPixmap] = None
        self._thumbnail_source_path: Optional[str] = None
        self._thumbnail_loading = False
        self._thumb_loading_anim_timer: Optional[QTimer] = None

        # Enable hover events for highlight effect
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        self.init_ui()
        self.setup_async_loader(
            loader_func=self._load_thumbnail_for_key,
            on_loaded=self._on_thumbnail_loaded,
            on_error=self._on_thumbnail_error,
            debounce_ms=THUMBNAIL_RELOAD_DEBOUNCE_MS,
            cache_enabled=True,
        )
        self.update_display(task)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Set fixed size for the widget
        self.setFixedSize(180, 180)
        
        # Set default style
        self.setStyleSheet("""
            EnhancedTaskItemWidget {
                background-color: #323436;
                border-radius: 8px;
            }
        """)

        # Initialize animation for waiting state
        self.waiting_movie = QMovie(":/icons/loading.gif")  # Using a generic loading icon
        if self.waiting_movie.isValid():
            self.waiting_movie.setScaledSize(self.size() / 4)
        else:
            # If no valid movie, create a simple placeholder
            self.waiting_movie = None

    def _project_path_for_task(self) -> Optional[str]:
        if hasattr(self.task, "task_manager") and hasattr(self.task.task_manager, "project"):
            return getattr(self.task.task_manager.project, "project_path", None)
        return None

    def _thumbnail_cache_key(self):
        config_path = getattr(self.task, "config_path", None) or ""
        mtime = 0
        if config_path and os.path.isfile(config_path):
            try:
                mtime = int(os.path.getmtime(config_path))
            except OSError:
                mtime = 0
        project_path = self._project_path_for_task() or ""
        task_path = getattr(self.task, "path", None) or ""
        return (config_path, project_path, task_path, mtime)

    def _load_thumbnail_for_key(self, key):
        config_path, project_path, task_path, _mtime = key
        if not config_path:
            return None
        pp = project_path or None
        tp = task_path or None
        return _resolve_task_thumbnail_path(config_path, pp, tp)

    def _on_thumbnail_loaded(self, key, resolved: Optional[str]):
        self._thumbnail_source_path = resolved
        if resolved and os.path.exists(resolved) and resolved.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif")
        ):
            self._thumbnail_pixmap = QPixmap(resolved)
            if self._thumbnail_pixmap.isNull():
                self._thumbnail_pixmap = None
        else:
            self._thumbnail_pixmap = None
        self._stop_thumb_loading_state()
        self.update()

    def _on_thumbnail_error(self, key, msg: str):
        logger.error("Thumbnail background load failed: %s", msg)
        self._thumbnail_pixmap = None
        self._thumbnail_source_path = None
        self._stop_thumb_loading_state()
        self.update()

    def _start_thumb_loading_animation(self):
        if self._thumb_loading_anim_timer is None:
            self._thumb_loading_anim_timer = QTimer(self)
            self._thumb_loading_anim_timer.timeout.connect(self.update)
        if not self._thumb_loading_anim_timer.isActive():
            self._thumb_loading_anim_timer.start(THUMBNAIL_LOADING_ANIM_INTERVAL_MS)

    def _stop_thumb_loading_state(self):
        self._thumbnail_loading = False
        if self._thumb_loading_anim_timer is not None:
            self._thumb_loading_anim_timer.stop()

    def _debounce_thumbnail_reload(self):
        """Coalesce rapid update_display calls (e.g. every progress tick)."""
        if self._thumbnail_pixmap is None or self._thumbnail_pixmap.isNull():
            self._thumbnail_loading = True
            self._start_thumb_loading_animation()
        key = self._thumbnail_cache_key()
        if not key[0]:
            self._stop_thumb_loading_state()
            self._thumbnail_pixmap = None
            self._thumbnail_source_path = None
            self.update()
            return
        self.schedule_async_load(key, force=False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            # Draw the main content area (thumbnail area)
            self.draw_thumbnail_area(painter)

            # Draw the special border with progress indicator
            self.draw_progress_border(painter)

            # Draw the task number bubble
            self.draw_task_number_bubble(painter)

            # Draw the central status indicator
            self.draw_status_indicator(painter)
        except Exception as e:
            logger.error(f"Error in paintEvent: {e}")
            # Draw a simple error indicator
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(self.rect(), Qt.AlignCenter, "Error")

    def draw_thumbnail_area(self, painter):
        """Draw the thumbnail area showing image/video preview or placeholder"""
        # Define the thumbnail rectangle (main content area)
        thumb_rect = self.rect().adjusted(2, 2, -2, -2)

        # Draw thumbnail background
        painter.fillRect(thumb_rect, QColor("#292b2e"))

        try:
            result_path = self._thumbnail_source_path
            pixmap = self._thumbnail_pixmap
            has_pixmap = pixmap is not None and not pixmap.isNull()

            if has_pixmap:
                scaled_pixmap = pixmap.scaled(
                    thumb_rect.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x = thumb_rect.x() + (thumb_rect.width() - scaled_pixmap.width()) // 2
                y = thumb_rect.y() + (thumb_rect.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
            elif self._thumbnail_loading:
                self.draw_thumbnail_loading(painter, thumb_rect)
            elif result_path and os.path.exists(result_path):
                if result_path.lower().endswith((".mp4", ".avi", ".mov", ".webm")):
                    self.draw_video_placeholder(painter, thumb_rect)
                else:
                    self.draw_placeholder(painter, thumb_rect)
            else:
                self.draw_placeholder(painter, thumb_rect)
        except Exception as e:
            logger.error(f"Error in draw_thumbnail_area: {e}")
            self.draw_placeholder(painter, thumb_rect)

    def draw_thumbnail_loading(self, painter, rect):
        """Lightweight loading hint in the thumbnail area (no extra I/O)."""
        painter.save()
        try:
            pen = QPen(QColor("#7eb8da"), 2)
            painter.setPen(pen)
            painter.setBrush(QColor("#7eb8da"))
            center_x = rect.center().x()
            center_y = rect.center().y()
            radius = 12
            t = QTime.currentTime().msec() / 1000.0
            rotation = t * 2 * math.pi
            for i in range(3):
                angle = rotation + (i * 2 * math.pi / 3)
                dot_x = center_x + radius * math.cos(angle)
                dot_y = center_y + radius * math.sin(angle)
                size = max(3.0, 5.0 - i)
                painter.drawEllipse(
                    int(dot_x - size / 2), int(dot_y - size / 2), int(size), int(size)
                )
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QColor("#8a8a8a"))
            hint = tr("Loading…")
            tw = painter.fontMetrics().horizontalAdvance(hint)
            painter.drawText(
                rect.x() + (rect.width() - tw) // 2,
                rect.bottom() - 8,
                hint,
            )
        except Exception as e:
            logger.error(f"Error in draw_thumbnail_loading: {e}")
        finally:
            painter.restore()

    def draw_video_placeholder(self, painter, rect):
        """Draw a video placeholder icon"""
        painter.save()
        try:
            # Draw a video camera-like icon
            pen = QPen(QColor("#a0a0a0"), 2)
            painter.setPen(pen)
            painter.setBrush(QColor(40, 42, 46))

            # Camera body - make sure the rect is large enough
            adjusted_rect = rect.adjusted(30, 50, -30, -50)
            if adjusted_rect.width() > 0 and adjusted_rect.height() > 0:
                painter.drawRoundedRect(adjusted_rect, 5, 5)

                # Lens
                lens_center = adjusted_rect.center()
                painter.drawEllipse(lens_center, 15, 15)

                # Triangle inside lens - Convert to QPoint list
                from PySide6.QtCore import QPoint
                points = [
                    QPoint(lens_center.x(), lens_center.y()-5),
                    QPoint(lens_center.x()-8, lens_center.y()+5),
                    QPoint(lens_center.x()+8, lens_center.y()+5)
                ]
                painter.drawPolygon(points)
        except Exception as e:
            logger.error(f"Error in draw_video_placeholder: {e}")
        finally:
            painter.restore()
    
    def draw_placeholder(self, painter, rect):
        """Draw a placeholder for when no results exist"""
        painter.save()
        try:
            # Draw the tool name and icon as placeholder
            pen = QPen(QColor("#a0a0a0"), 1)
            painter.setPen(pen)

            # Get the tool name and icon
            tool_name = getattr(self.task, 'tool', 'unknown')

            # Calculate text positioning
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)

            # Get text metrics
            fm = painter.fontMetrics()
            text = tr(f"Tool: {tool_name}")
            text_width = fm.horizontalAdvance(text)
            text_height = fm.height()

            # Center the text
            x = rect.x() + (rect.width() - text_width) // 2
            y = rect.y() + (rect.height() - text_height) // 2

            painter.drawText(x, y, text)
        except Exception as e:
            logger.error(f"Error in draw_placeholder: {e}")
        finally:
            painter.restore()

    def draw_progress_border(self, painter):
        """Draw a special border with progress indicator"""
        # This method doesn't use painter.save/restore so no need to change the exception handling structure
        try:
            progress = getattr(self.task, 'percent', 0) / 100  # Convert to 0-1 range

            # Define the border rectangle
            border_width = 3
            border_rect = self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2)

            # Calculate path length and positions for progress indicator
            total_length = 2 * (border_rect.width() + border_rect.height()) - 4  # Perimeter minus corners
            progress_length = total_length * progress

            # Draw the border based on the task status
            status = getattr(self.task, 'status', 'running')

            # Determine the color based on status
            if status == 'completed':
                border_color = QColor(0, 255, 0)  # Green for completed
            elif status == 'running':
                border_color = QColor(0, 128, 255)  # Blue for running
            elif status == 'checking':
                border_color = QColor(0, 255, 128)  # Light green for checking
            elif status == 'failed':
                border_color = QColor(255, 0, 0)  # Red for failed
            else:
                border_color = QColor(128, 128, 128)  # Gray for other statuses

            pen = QPen(border_color, border_width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)

            # Create path for the border
            path = QPainterPath()

            # Move to bottom-left (start position)
            path.moveTo(border_rect.left(), border_rect.bottom())

            # Bottom side - from left to right
            bottom_end_x = border_rect.left() + min(progress_length, border_rect.width())
            path.lineTo(bottom_end_x, border_rect.bottom())

            remaining = progress_length - border_rect.width()
            if remaining > 0:
                # Right side - from bottom to top
                right_end_y = border_rect.bottom() - min(remaining, border_rect.height())
                path.lineTo(border_rect.right(), right_end_y)

                remaining -= border_rect.height()
                if remaining > 0:
                    # Top side - from right to left
                    top_end_x = border_rect.right() - min(remaining, border_rect.width())
                    path.lineTo(top_end_x, border_rect.top())

                    remaining -= border_rect.width()
                    if remaining > 0:
                        # Left side - from top to bottom
                        left_end_y = border_rect.top() + min(remaining, border_rect.height())
                        path.lineTo(border_rect.left(), left_end_y)

            painter.drawPath(path)
        except Exception as e:
            logger.error(f"Error in draw_progress_border: {e}")

    def draw_task_number_bubble(self, painter):
        """Draw a colorful bubble for the task number in the top-right corner"""
        painter.save()
        try:
            # Bubble properties
            bubble_size = 20
            margin = 5

            # Position in top-right corner
            x = self.width() - bubble_size - margin
            y = margin

            # Draw bubble background
            status = getattr(self.task, 'status', 'running')
            if status == 'completed':
                bubble_color = QColor(0, 200, 0)  # Green
            elif status == 'running':
                bubble_color = QColor(0, 150, 255)  # Blue
            elif status == 'checking':
                bubble_color = QColor(0, 200, 150)  # Cyan
            elif status == 'failed':
                bubble_color = QColor(200, 0, 0)  # Red
            else:
                bubble_color = QColor(150, 150, 150)  # Gray

            painter.setBrush(bubble_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x, y, bubble_size, bubble_size)

            # Draw task number
            painter.setPen(QColor(255, 255, 255))
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)

            text = str(getattr(self.task, 'task_id', ''))
            text_width = painter.fontMetrics().horizontalAdvance(text)
            text_height = painter.fontMetrics().height()

            text_x = x + (bubble_size - text_width) // 2
            text_y = y + (bubble_size + text_height) // 2  # Adjust for baseline

            painter.drawText(text_x, text_y, text)
        except Exception as e:
            logger.error(f"Error in draw_task_number_bubble: {e}")
        finally:
            painter.restore()

    def draw_status_indicator(self, painter):
        """Draw central status indicators (waiting animation, countdown, duration)"""
        painter.save()
        try:
            status = getattr(self.task, 'status', 'running')

            if status == 'running':
                # Show countdown timer
                painter.setPen(QColor(0, 255, 255))  # Cyan color for running state

                # Calculate estimated time remaining based on progress
                # For now we'll simulate it
                # In real implementation, this would be calculated based on progress speed
                estimated_time = self.calculate_estimated_time_remaining()

                font = QFont()
                font.setPointSize(12)
                font.setBold(True)
                painter.setFont(font)

                text_width = painter.fontMetrics().horizontalAdvance(estimated_time)
                text_height = painter.fontMetrics().height()

                text_x = (self.width() - text_width) // 2
                text_y = (self.height() + text_height) // 2  # Adjust for baseline

                painter.drawText(text_x, text_y, estimated_time)
            elif status in ['created', 'waiting', 'queued']:
                # Show waiting animation
                if self.waiting_movie:
                    # Start the animation if not already running
                    if self.waiting_movie.state() != QMovie.Running:
                        self.waiting_movie.start()

                    # Draw current frame of the movie
                    frame = self.waiting_movie.currentPixmap()
                    if not frame.isNull():
                        pos_x = (self.width() - frame.width()) // 2
                        pos_y = (self.height() - frame.height()) // 2
                        painter.drawPixmap(pos_x, pos_y, frame)
                else:
                    # Draw a simple rotating indicator
                    painter.setPen(QColor(150, 150, 150))
                    painter.setBrush(QColor(150, 150, 150))

                    # Draw a rotating indicator with multiple dots
                    from PySide6.QtCore import QTime
                    import math
                    current_time = QTime.currentTime()
                    rotation_factor = (current_time.msec() / 1000.0) * 2 * math.pi  # Full rotation every second

                    center_x = self.width() // 2
                    center_y = self.height() // 2
                    radius = 15

                    # Draw 3 rotating dots
                    for i in range(3):
                        angle = rotation_factor + (i * 2 * math.pi / 3)
                        dot_x = center_x + radius * math.cos(angle)
                        dot_y = center_y + radius * math.sin(angle)
                        size = 6 - i  # Different sizes for depth effect

                        painter.drawEllipse(int(dot_x - size/2), int(dot_y - size/2), int(size), int(size))
            elif status == 'completed':
                # Show execution duration
                duration = getattr(self.task, 'duration', self.calculate_execution_duration())

                painter.setPen(QColor(0, 255, 0))  # Green color for completed state
                font = QFont()
                font.setPointSize(12)
                font.setBold(True)
                painter.setFont(font)

                text_width = painter.fontMetrics().horizontalAdvance(duration)
                text_height = painter.fontMetrics().height()

                text_x = (self.width() - text_width) // 2
                text_y = (self.height() + text_height) // 2  # Adjust for baseline

                painter.drawText(text_x, text_y, duration)
            elif status == 'failed':
                # Show failure indicator
                painter.setPen(QColor(255, 50, 50))  # Red color for failed state
                font = QFont()
                font.setPointSize(16)
                font.setBold(True)
                painter.setFont(font)

                text = "✗"
                text_width = painter.fontMetrics().horizontalAdvance(text)
                text_height = painter.fontMetrics().height()

                text_x = (self.width() - text_width) // 2
                text_y = (self.height() + text_height) // 2  # Adjust for baseline

                painter.drawText(text_x, text_y, text)
            elif status == 'checking':
                # Show checking indicator (rotating circle)
                painter.setPen(QColor(0, 255, 150))  # Light green for checking state
                painter.setBrush(Qt.NoBrush)

                center_x = self.width() // 2
                center_y = self.height() // 2
                radius = 15

                # Draw a rotating arc
                from PySide6.QtCore import QTime
                import math
                current_time = QTime.currentTime()
                start_angle = int((current_time.msec() / 1000.0) * 180)  # Degrees
                span_angle = 90  # 90 degree arc

                painter.drawArc(
                    int(center_x - radius), int(center_y - radius),
                    int(2 * radius), int(2 * radius),
                    (start_angle % 360) * 16, span_angle * 16  # Qt uses 1/16th degree units
                )
        except Exception as e:
            logger.error(f"Error in draw_status_indicator: {e}")
        finally:
            painter.restore()

    def calculate_estimated_time_remaining(self):
        """Calculate estimated time remaining based on progress"""
        # Simple estimation: if 50% done in 10 seconds, estimate 10 more seconds
        # In practice, this should use actual progress speed
        try:
            percent = getattr(self.task, 'percent', 0)
            if percent > 0 and percent < 100:
                # Assume started at 0% at time 0 for simplicity
                # In reality, you'd track the start time
                completed_fraction = percent / 100.0
                # Just return a placeholder; actual implementation would track timing
                remaining_seconds = int((100 - percent) / (percent / 10)) if percent > 0 else 30
                minutes = remaining_seconds // 60
                seconds = remaining_seconds % 60
                return f"{minutes:02d}:{seconds:02d}"
        except:
            pass
        return "00:30"  # Default fallback

    def calculate_execution_duration(self):
        """Calculate total execution duration"""
        # In practice, this would use actual start and end times
        # For now, just return a placeholder
        try:
            # If we have a start time in the task options, calculate the difference
            if hasattr(self.task, 'start_time'):
                import time
                elapsed = int(time.time() - self.task.start_time)
                minutes = elapsed // 60
                seconds = elapsed % 60
                return f"{minutes:02d}:{seconds:02d}"
        except:
            pass
        return "00:15"  # Default fallback

    def mousePressEvent(self, event):
        """Handle mouse click events"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)  # Emit the clicked signal with this widget as parameter

    def set_selected(self, selected):
        """Set the selected state and update appearance"""
        self.is_selected = selected
        if selected:
            # Apply selection style
            self.setStyleSheet("""
                EnhancedTaskItemWidget {
                    background-color: #4a4c5f;
                    border: 2px solid white;
                    border-radius: 8px;
                }
            """)
        else:
            # Restore original style
            self.setStyleSheet("""
                EnhancedTaskItemWidget {
                    background-color: #323436;
                    border-radius: 8px;
                }
            """)
        self.update()  # Trigger repaint

    def update_display(self, task):
        """Update the display with new task information"""
        old_id = getattr(self.task, "task_id", None)
        new_id = getattr(task, "task_id", None)
        if old_id != new_id:
            self._stop_thumb_loading_state()
            self.cancel_async_pending()
            self.invalidate_async_cache()
            self._thumbnail_pixmap = None
            self._thumbnail_source_path = None
            self.task = task
            self._thumbnail_loading = True
            self._start_thumb_loading_animation()
            key = self._thumbnail_cache_key()
            if key[0]:
                self.schedule_async_load(key, force=True)
            else:
                self._stop_thumb_loading_state()
            self.update()
            return
        self.task = task
        self._debounce_thumbnail_reload()
        self.update()  # Trigger repaint

    def enterEvent(self, event):
        """When mouse enters the widget, apply highlight effect"""
        self.setStyleSheet("""
            EnhancedTaskItemWidget {
                background-color: #3a3c3f;
                border-radius: 8px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """When mouse leaves the widget, remove highlight effect but maintain selected state"""
        if self.is_selected:
            # Keep selected style when leaving
            self.setStyleSheet("""
                EnhancedTaskItemWidget {
                    background-color: #4a4c5f;
                    border: 2px solid white;
                    border-radius: 8px;
                }
            """)
        else:
            # Restore original style if not selected
            self.setStyleSheet("""
                EnhancedTaskItemWidget {
                    background-color: #323436;
                    border-radius: 8px;
                }
            """)
        super().leaveEvent(event)