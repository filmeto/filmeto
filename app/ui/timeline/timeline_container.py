"""
Timeline Container Widget

This widget provides a container for the timeline that draws a vertical cursor line
following the mouse position. The line is drawn on top of all timeline content
including cards, and mouse tracking works across all child widgets.
"""

import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QPoint, QEvent, QPointF, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QHoverEvent, QPolygonF, QMouseEvent
from typing import Tuple, Optional

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.signals import Signals
from app.ui.timeline.video_timeline import VideoTimeline
from app.ui.timeline.screenplay_timeline import ScreenplayTimeline
from app.ui.timeline.story_board_timeline import StoryBoardTimeline
from app.ui.timeline.subtitle_timeline import SubtitleTimeline
from app.ui.timeline.voice_timeline import VoiceTimeline
from utils.i18n_utils import tr
from utils.qt_utils import widget_left_x_in_content

logger = logging.getLogger(__name__)

# Matches VideoTimelineCard / screenplay cards and timeline_layout (margins 5, spacing 5).
VIDEO_TIMELINE_CARD_WIDTH = 90
VIDEO_TIMELINE_CARD_SPACING = 5
VIDEO_TIMELINE_CONTENT_MARGIN = 5


class TimelinePositionLineOverlay(QWidget):

    def __init__(self, parent, timeline_position, timeline_x):
        super().__init__(parent)

        # Set transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Don't accept focus to avoid interfering with timeline
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # This widget should not block mouse events for clicking
        # but we'll track position via parent's event filter
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.timeline_position=timeline_position
        self.timeline_x = timeline_x
        self.scroll_offset = 0  # Current horizontal scroll offset
        self._mouse_x = None
        
        # Throttle timer for cursor updates (limits update frequency while staying responsive)
        self._cursor_update_timer = QTimer(self)
        self._cursor_update_timer.setSingleShot(True)
        self._cursor_update_timer.setInterval(8)  # ~120 FPS max (8ms)
        self._cursor_update_timer.timeout.connect(self._reset_cursor_throttle)
        self._cursor_throttle_active = False
        
        # Separate flags to track what needs updating
        self._cursor_dirty = False
        self._timeline_dirty = False

    def paintEvent(self, event):
        if self._mouse_x is None and self.timeline_x is None:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw timeline position line (higher priority, drawn first so cursor can overlay)
        if self.timeline_x is not None:
            # Apply coordinate transformation: viewport_x = content_x - scroll_offset
            viewport_x = self.timeline_x - self.scroll_offset
            
            # Only draw if within visible bounds
            if 0 <= viewport_x <= self.width():
                # Draw the vertical line
                pen = QPen(QColor(255, 255, 255, 255))
                pen.setWidth(4)
                pen.setStyle(Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                painter.drawLine(viewport_x, 0, viewport_x, self.height())
                
                # Draw solid triangles at both ends
                # Triangle size
                triangle_size = 8
                
                # Set brush for filled triangles
                painter.setBrush(QColor(255, 255, 255, 255))
                painter.setPen(Qt.PenStyle.NoPen)  # No outline
                
                # Top triangle (pointing up)
                top_triangle = QPolygonF([
                    QPointF(viewport_x, triangle_size),  # Bottom center point
                    QPointF(viewport_x - triangle_size, 0),  # Top left
                    QPointF(viewport_x + triangle_size, 0)   # Top right
                ])
                painter.drawPolygon(top_triangle)
                
                # Bottom triangle (pointing down)
                bottom_y = self.height()
                bottom_triangle = QPolygonF([
                    QPointF(viewport_x, bottom_y - triangle_size),  # Top center point
                    QPointF(viewport_x - triangle_size, bottom_y),  # Bottom left
                    QPointF(viewport_x + triangle_size, bottom_y)   # Bottom right
                ])
                painter.drawPolygon(bottom_triangle)
        
        # Draw mouse cursor line (drawn second to overlay on top if needed)
        if self._mouse_x is not None:
            pen = QPen(QColor(255, 255, 255, 200))
            pen.setWidth(1)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self._mouse_x, 0, self._mouse_x, self.height())
        
        painter.end()
        
        # Reset dirty flags after painting
        self._cursor_dirty = False
        self._timeline_dirty = False

    def on_timeline_position(self, timeline_position, timeline_x, scroll_offset):
        """Update timeline position - immediate update for accuracy"""
        self.timeline_position = timeline_position
        self.timeline_x = timeline_x
        self.scroll_offset = scroll_offset
        self._timeline_dirty = True
        
        # Timeline updates are critical, apply immediately
        self.update()
    
    def update_scroll_offset(self, scroll_offset):
        """Update scroll offset and trigger repaint"""
        if self.scroll_offset != scroll_offset:
            self.scroll_offset = scroll_offset
            self.update()

    def set_cursor_position(self, x):
        """Update cursor line position - throttled to limit update frequency"""
        if self._mouse_x != x:
            self._mouse_x = x
            self._cursor_dirty = True
            
            # Throttle: Update immediately if not throttled, otherwise skip
            if not self._cursor_throttle_active:
                self.update()
                self._cursor_throttle_active = True
                self._cursor_update_timer.start()
    
    def _reset_cursor_throttle(self):
        """Reset throttle flag to allow next cursor update"""
        self._cursor_throttle_active = False

    def clear_cursor(self):
        """Hide the cursor line - immediate update"""
        if self._mouse_x is not None:
            # Reset throttle state
            self._cursor_update_timer.stop()
            self._cursor_throttle_active = False
            
            self._mouse_x = None
            self._cursor_dirty = True
            self.update()

class TimelineDividerLinesOverlay(QWidget):
    """
    Transparent overlay widget that draws divider lines between the three timeline sections.
    This helps visually distinguish between subtitle, main timeline, and voiceover sections.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # This widget should not block mouse events
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Store positions for the divider lines
        self._subtitle_height = 0
        self._voiceover_top = 0
        
    def set_divider_positions(self, subtitle_height, voiceover_top):
        """Update divider line positions"""
        self._subtitle_height = subtitle_height
        self._voiceover_top = voiceover_top
        self.update()
    
    def paintEvent(self, event):
        """Draw the divider lines"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw dashed lines
        pen = QPen(QColor(100, 100, 100, 150))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        # Draw line below subtitle timeline
        if self._subtitle_height > 0:
            painter.drawLine(0, self._subtitle_height, self.width(), self._subtitle_height)
            
        # Draw line above voiceover timeline
        if self._voiceover_top > 0:
            painter.drawLine(0, self._voiceover_top, self.width(), self._voiceover_top)
            
        painter.end()


class TimelineContainer(BaseWidget):
    """
    Container widget for the timeline that displays a vertical cursor line.
    
    Uses a transparent overlay to draw the cursor line on top of all timeline
    content while preserving all timeline functionality. Mouse events are tracked
    globally across the container and all child widgets.
    """

    def __init__(self, parent, workspace:Workspace):
        """
        Initialize the timeline container.
        
        Args:
            timeline_widget: The HorizontalTimeline widget to wrap
            parent: Parent widget
        """
        super(TimelineContainer, self).__init__(workspace)
        self.workspace = workspace
        # Legacy layout constants (unified width estimate; per-mode hit-testing uses widget geometry).
        self.card_width = VIDEO_TIMELINE_CARD_WIDTH
        self.card_spacing = VIDEO_TIMELINE_CARD_SPACING
        self.content_margin_left = VIDEO_TIMELINE_CONTENT_MARGIN
        # All timeline rows live under _timeline_content so indicator overlays (direct
        # children of self) stay above them in the stacking order without raise()/timers.
        self._timeline_content = QWidget(self)
        self.main_layout = QVBoxLayout(self._timeline_content)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._timeline_content)

        # Create the main timeline widget (VideoTimeline - immediately required)
        self.video_timeline = VideoTimeline(self._timeline_content, workspace)
        self.main_layout.addWidget(self.video_timeline)

        # Placeholders for secondary timelines (lazy loaded)
        self.subtitle_timeline = None
        self.voice_timeline = None
        self.script_timeline: Optional[ScreenplayTimeline] = None
        self.story_board_timeline: Optional[StoryBoardTimeline] = None
        self._secondary_timelines_loaded = False
        self._timeline_mode = "video"

        # Scroll synchronization state
        self._scroll_sync_active = False  # Flag to prevent feedback loops
        self._last_scroll_position = 0  # Cache last synchronized scroll value

        # Overlays are siblings of _timeline_content; create after content exists.
        # Divider under playhead: create divider first, then position line (last = topmost).
        self.divider_overlay = TimelineDividerLinesOverlay(self)
        timeline_position = self.workspace.get_project().get_timeline_position()
        timeline_x, card_index = self.calculate_timeline_x(timeline_position)
        self.timeline_position_overlay = TimelinePositionLineOverlay(
            self, timeline_position, timeline_x
        )

        # Enable hover events to track mouse globally
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setMouseTracking(True)

        # Enable mouse press events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Connect to signals for card selection
        Signals().connect(Signals.TIMELINE_POSITION_CLICKED, self._on_timeline_position_clicked_for_selection)
        Signals().connect(Signals.TIMELINE_POSITION_STOPPED, self._on_timeline_position_stopped_for_selection)

        # Track last processed click event to prevent duplicate triggers
        self._last_click_event = None

        # Install event filter to intercept mouse clicks from child widgets
        self.installEventFilter(self)
        self._install_event_filters_recursively(self.video_timeline)

        # Initialize scroll offset after overlay creation
        initial_scroll_offset = self.video_timeline.scroll_area.horizontalScrollBar().value()
        self.timeline_position_overlay.update_scroll_offset(initial_scroll_offset)

        # Delay load secondary timelines (subtitle, voice) after window is displayed
        # This speeds up initial window display
        QTimer.singleShot(100, self._load_secondary_timelines)

        Signals().connect(Signals.TIMELINE_MODE_CHANGED, self._on_timeline_mode_signal)

    def _make_timeline_mode_placeholder(self, object_name: str, message: str) -> QFrame:
        frame = QFrame(self._timeline_content)
        frame.setObjectName(object_name)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel(message, frame)
        label.setObjectName(f"{object_name}_label")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        frame.setMinimumHeight(120)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return frame

    def _on_timeline_mode_signal(self, sender, params=None, **kwargs):
        if params is None:
            return
        self.set_timeline_mode(params)

    def set_timeline_mode(self, mode: str) -> None:
        valid = frozenset({"script", "storyboard", "video"})
        if mode not in valid:
            return
        self._timeline_mode = mode
        self._apply_timeline_mode_visibility()

    def _apply_timeline_mode_visibility(self) -> None:
        if not self._secondary_timelines_loaded:
            self.video_timeline.setVisible(True)
            return
        mode = self._timeline_mode
        if self.script_timeline is not None:
            self.script_timeline.setVisible(mode == "script")
        if self.story_board_timeline is not None:
            self.story_board_timeline.setVisible(mode == "storyboard")
        show_video_stack = mode == "video"
        self.video_timeline.setVisible(show_video_stack)
        if self.subtitle_timeline is not None:
            self.subtitle_timeline.setVisible(show_video_stack)
        if self.voice_timeline is not None:
            self.voice_timeline.setVisible(show_video_stack)
        self._update_divider_positions()

    def _load_secondary_timelines(self):
        """Load screenplay/storyboard placeholders and subtitle/voice timelines after first paint."""
        if self._secondary_timelines_loaded:
            return

        self._secondary_timelines_loaded = True
        logger.info("Loading secondary timelines (script, storyboard, subtitle, voice)...")

        # Timer to detect when scrolling has stopped (for cursor show/hide)
        self._scroll_stop_timer = QTimer(self)
        self._scroll_stop_timer.setSingleShot(True)
        self._scroll_stop_timer.setInterval(100)  # 100ms delay after scroll stops
        self._scroll_stop_timer.timeout.connect(self._on_scroll_stopped)

        self.script_timeline = ScreenplayTimeline(self._timeline_content, self.workspace)
        self.story_board_timeline = StoryBoardTimeline(self._timeline_content, self.workspace)

        self.subtitle_timeline = SubtitleTimeline(self._timeline_content, self.workspace)
        self.voice_timeline = VoiceTimeline(self._timeline_content, self.workspace)

        self._install_event_filters_recursively(self.script_timeline)
        self._install_event_filters_recursively(self.story_board_timeline)
        self._install_event_filters_recursively(self.subtitle_timeline)
        self._install_event_filters_recursively(self.voice_timeline)

        # Vertical order: screenplay, storyboard, then subtitle → video → voice (merged video stack)
        self.main_layout.insertWidget(0, self.script_timeline)
        self.main_layout.insertWidget(1, self.story_board_timeline)
        self.main_layout.insertWidget(2, self.subtitle_timeline)
        self.main_layout.insertWidget(4, self.voice_timeline)

        self.setup_scroll_synchronization()
        self._apply_timeline_mode_visibility()

        logger.info("Secondary timelines loaded successfully")

    def _ensure_secondary_timelines_loaded(self):
        """Ensure secondary timelines are loaded before accessing them"""
        if not self._secondary_timelines_loaded:
            self._load_secondary_timelines()

    def _install_event_filters_recursively(self, widget):
        """Install event filter on widget and all its children recursively"""
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)
    
    def setup_scroll_synchronization(self):
        """
        Setup scroll synchronization between all three timelines.
        Connects scrollbar valueChanged signals to the synchronization handler.
        """
        video_scrollbar = self.video_timeline.scroll_area.get_horizontal_scrollbar()
        script_scrollbar = self.script_timeline.scroll_area.get_horizontal_scrollbar()
        story_scrollbar = self.story_board_timeline.scroll_area.get_horizontal_scrollbar()
        subtitle_scrollbar = self.subtitle_timeline.scroll_area.get_horizontal_scrollbar()
        voice_scrollbar = self.voice_timeline.scroll_area.get_horizontal_scrollbar()

        video_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('video', value))
        script_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('script', value))
        story_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('storyboard', value))
        subtitle_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('subtitle', value))
        voice_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('voice', value))

        self.video_timeline.scroll_area.scroll_started.connect(self._on_scroll_started)
        self.script_timeline.scroll_area.scroll_started.connect(self._on_scroll_started)
        self.story_board_timeline.scroll_area.scroll_started.connect(self._on_scroll_started)
        self.subtitle_timeline.scroll_area.scroll_started.connect(self._on_scroll_started)
        self.voice_timeline.scroll_area.scroll_started.connect(self._on_scroll_started)
        
        # Calculate and set unified content width
        self.update_unified_scroll_range()
    
    def _on_scroll_value_changed(self, source_timeline: str, new_value: int):
        """
        Handle scroll value change from any timeline.
        Synchronizes the scroll position across all timelines.

        Args:
            source_timeline: Which timeline triggered the scroll ('video', 'subtitle', or 'voice')
            new_value: New scroll position value
        """
        # Ensure secondary timelines are loaded before trying to sync
        if not self._secondary_timelines_loaded:
            return

        # Prevent feedback loops - if we're already syncing, ignore
        if self._scroll_sync_active:
            return

        # Only sync if value actually changed (optimization)
        if new_value == self._last_scroll_position:
            return

        # Set sync flag to prevent feedback loops
        self._scroll_sync_active = True
        self._last_scroll_position = new_value

        try:
            # Sync to other timelines
            if source_timeline != 'video':
                self.video_timeline.scroll_area.get_horizontal_scrollbar().setValue(new_value)
            if source_timeline != 'script' and self.script_timeline:
                self.script_timeline.scroll_area.get_horizontal_scrollbar().setValue(new_value)
            if source_timeline != 'storyboard' and self.story_board_timeline:
                self.story_board_timeline.scroll_area.get_horizontal_scrollbar().setValue(new_value)
            if source_timeline != 'subtitle' and self.subtitle_timeline:
                self.subtitle_timeline.scroll_area.get_horizontal_scrollbar().setValue(new_value)
            if source_timeline != 'voice' and self.voice_timeline:
                self.voice_timeline.scroll_area.get_horizontal_scrollbar().setValue(new_value)

            # Update overlay scroll offset
            self.timeline_position_overlay.update_scroll_offset(new_value)
        finally:
            # Always reset sync flag
            self._scroll_sync_active = False

        # Reset the scroll stop timer (scrolling is still active)
        self._scroll_stop_timer.start()
    
    def _on_scroll_started(self):
        """
        Handle scroll started event.
        Hides cursor overlay during scrolling for performance.
        """
        # Hide cursor during scrolling (performance optimization)
        self.timeline_position_overlay.clear_cursor()
    
    def _on_scroll_stopped(self):
        """
        Handle scroll stopped event.
        Restores cursor overlay after scrolling stops.
        """
        # Cursor will be shown again when mouse moves (handled by event())
        pass
    
    def update_unified_scroll_range(self):
        """
        Calculate and apply unified scroll range to all timelines.
        This ensures all timelines have the same scrollable width.
        """
        width = self.get_timeline_content_width()

        # Set content width for video timeline (always available)
        self.video_timeline.content_widget.setMinimumWidth(width)

        if self._secondary_timelines_loaded:
            if self.script_timeline:
                self.script_timeline.set_content_width(width)
            if self.story_board_timeline:
                self.story_board_timeline.set_content_width(width)
            if self.subtitle_timeline:
                self.subtitle_timeline.set_content_width(width)
            if self.voice_timeline:
                self.voice_timeline.set_content_width(width)

    def _width_for_horizontal_cards(self, card_count: int) -> int:
        if card_count == 0:
            return 800
        total_width = (VIDEO_TIMELINE_CARD_WIDTH + VIDEO_TIMELINE_CARD_SPACING) * card_count
        total_width += VIDEO_TIMELINE_CONTENT_MARGIN * 2
        total_width += 100
        total_width += 100
        return total_width

    def _effective_timeline_mode(self) -> str:
        if not self._secondary_timelines_loaded:
            return "video"
        return self._timeline_mode

    def _content_widget_for_mode(self, mode: str):
        if mode == "script" and self._secondary_timelines_loaded and self.script_timeline:
            return self.script_timeline.content_widget
        if mode == "storyboard" and self._secondary_timelines_loaded and self.story_board_timeline:
            return self.story_board_timeline.content_widget
        return self.video_timeline.content_widget

    def _container_point_to_content_x(self, container_point: QPoint, mode: str) -> float:
        cw = self._content_widget_for_mode(mode)
        g = self.mapToGlobal(container_point)
        return float(cw.mapFromGlobal(g).x())

    def _video_card_geometry(self):
        """Returns list of (left, width, next_left, 1-based index) in video content_widget coords."""
        vt = self.video_timeline
        cards = getattr(vt, "cards", None) or []
        if not cards:
            return []
        cw = vt.content_widget
        out = []
        n = len(cards)
        for i, card in enumerate(cards):
            left = float(card.mapTo(cw, QPoint(0, 0)).x())
            w = float(card.width())
            next_left = (
                float(cards[i + 1].mapTo(cw, QPoint(0, 0)).x()) if i + 1 < n else left + w
            )
            out.append((left, w, next_left, i + 1))
        return out

    def _script_segment_durations(self, project) -> list:
        st = self.script_timeline
        if not st or not st.cards:
            return []
        n = len(st.cards)
        n_vid = len(self.video_timeline.cards) if self.video_timeline.cards else 0
        total = project.calculate_timeline_duration()
        if n_vid > 0 and n == n_vid:
            return [project.get_item_duration(i + 1) for i in range(n)]
        if n <= 0:
            return []
        share = total / n if total > 0 else 0.0
        return [share] * n

    def _calculate_timeline_position_video(self, content_x: float, project) -> Tuple[float, int]:
        geom = self._video_card_geometry()
        if not geom:
            return 0.0, 0
        first_left = geom[0][0]
        if content_x < first_left:
            return 0.0, 0
        accumulated = 0.0
        for left, w, next_left, idx in geom:
            try:
                dur = project.get_item_duration(idx)
            except Exception as e:
                logger.error("Error getting duration for card %s: %s", idx, e)
                dur = 1.0
            if content_x < left:
                break
            if content_x < left + w:
                frac = (content_x - left) / w if w > 0 else 0.0
                return round(accumulated + frac * dur, 3), idx
            if content_x < next_left:
                return round(accumulated + dur, 3), idx
            accumulated += dur
        last_idx = len(geom)
        return round(accumulated, 3), last_idx

    def _calculate_timeline_x_video(self, timeline_position: float, project) -> Tuple[int, int]:
        geom = self._video_card_geometry()
        if not geom:
            return 0, 0
        if timeline_position <= 0:
            return int(round(geom[0][0])), 0
        accumulated = 0.0
        last_i = len(geom) - 1
        for i, (left, w, _next_left, idx) in enumerate(geom):
            try:
                dur = project.get_item_duration(idx)
            except Exception as e:
                logger.error("Error getting duration for card %s: %s", idx, e)
                dur = 1.0
            start_t = accumulated
            end_t = accumulated + dur
            is_last = i == last_i
            if (start_t <= timeline_position < end_t) or (is_last and timeline_position >= start_t):
                time_in = timeline_position - start_t
                if dur > 0:
                    time_in = min(max(time_in, 0.0), dur)
                frac = time_in / dur if dur > 0 else 0.0
                x = left + frac * w
                return int(round(x)), idx
            accumulated = end_t
        last = geom[-1]
        return int(round(last[0] + last[1])), last[3]

    def _calculate_timeline_position_script(self, content_x: float, project) -> Tuple[float, int]:
        st = self.script_timeline
        if not st or not st.cards:
            return 0.0, 0
        cw = st.content_widget
        durs = self._script_segment_durations(project)
        if not durs or len(durs) != len(st.cards):
            return 0.0, 0
        first = st.cards[0]
        first_left = float(first.mapTo(cw, QPoint(0, 0)).x())
        if content_x < first_left:
            return 0.0, 0
        accumulated = 0.0
        n = len(st.cards)
        for i, card in enumerate(st.cards):
            left = float(card.mapTo(cw, QPoint(0, 0)).x())
            w = float(card.width())
            next_left = (
                float(st.cards[i + 1].mapTo(cw, QPoint(0, 0)).x()) if i + 1 < n else left + w
            )
            dur = durs[i]
            idx = i + 1
            if content_x < left:
                break
            if content_x < left + w:
                frac = (content_x - left) / w if w > 0 else 0.0
                return round(accumulated + frac * dur, 3), idx
            if content_x < next_left:
                return round(accumulated + dur, 3), idx
            accumulated += dur
        return round(accumulated, 3), n

    def _calculate_timeline_x_script(self, timeline_position: float, project) -> Tuple[int, int]:
        st = self.script_timeline
        if not st or not st.cards:
            return 0, 0
        cw = st.content_widget
        durs = self._script_segment_durations(project)
        if not durs or len(durs) != len(st.cards):
            return 0, 0
        if timeline_position <= 0:
            c0 = st.cards[0]
            return int(round(float(c0.mapTo(cw, QPoint(0, 0)).x()))), 0
        accumulated = 0.0
        n = len(st.cards)
        last_i = n - 1
        for i, card in enumerate(st.cards):
            left = float(card.mapTo(cw, QPoint(0, 0)).x())
            w = float(card.width())
            dur = durs[i]
            idx = i + 1
            start_t = accumulated
            end_t = accumulated + dur
            is_last = i == last_i
            if (start_t <= timeline_position < end_t) or (is_last and timeline_position >= start_t):
                time_in = timeline_position - start_t
                if dur > 0:
                    time_in = min(max(time_in, 0.0), dur)
                frac = time_in / dur if dur > 0 else 0.0
                x = left + frac * w
                return int(round(x)), idx
            accumulated = end_t
        last = st.cards[-1]
        ll = float(last.mapTo(cw, QPoint(0, 0)).x())
        return int(round(ll + float(last.width()))), n

    def _storyboard_scene_time_weights(self, project) -> tuple:
        st = self.story_board_timeline
        scenes = getattr(st, "scene_cards", None) or []
        if not scenes:
            return [], 0.0
        widths = [float(c.width()) for c in scenes]
        tw = sum(widths)
        total_dur = project.calculate_timeline_duration()
        if tw <= 0 or total_dur <= 0:
            return [], 0.0
        weights = [w / tw for w in widths]
        return list(zip(scenes, weights, widths)), total_dur

    def _calculate_timeline_position_storyboard(self, content_x: float, project) -> Tuple[float, int]:
        st = self.story_board_timeline
        cw = st.content_widget
        data, total_dur = self._storyboard_scene_time_weights(project)
        if not data:
            return 0.0, 0
        t_acc = 0.0
        for card, weight, w_scene in data:
            left = widget_left_x_in_content(card, cw)
            right = left + w_scene
            t_scene = total_dur * weight
            if content_x < left:
                return round(max(0.0, t_acc), 3), 0
            shots = card.shot_widgets
            if not shots:
                if left <= content_x < right:
                    frac = (content_x - left) / w_scene if w_scene > 0 else 0.0
                    return round(t_acc + frac * t_scene, 3), 0
                t_acc += t_scene
                continue
            shot_lefts = [widget_left_x_in_content(sh, cw) for sh in shots]
            shot_ws = [float(sh.width()) for sh in shots]
            sw = sum(shot_ws)
            if sw <= 0:
                t_acc += t_scene
                continue
            t_shots = [t_scene * (swi / sw) for swi in shot_ws]
            for j, sh in enumerate(shots):
                sl, sr = shot_lefts[j], shot_lefts[j] + shot_ws[j]
                td = t_shots[j]
                if content_x < sl:
                    return round(t_acc, 3), 0
                if content_x < sr:
                    frac = (content_x - sl) / shot_ws[j] if shot_ws[j] > 0 else 0.0
                    return round(t_acc + frac * td, 3), 0
                t_acc += td
            if left <= content_x < right:
                return round(t_acc, 3), 0
        return round(total_dur, 3), 0

    def _calculate_timeline_x_storyboard(self, timeline_position: float, project) -> Tuple[int, int]:
        st = self.story_board_timeline
        cw = st.content_widget
        data, total_dur = self._storyboard_scene_time_weights(project)
        if not data or total_dur <= 0:
            return 0, 0
        if timeline_position <= 0:
            c0 = data[0][0]
            return int(round(widget_left_x_in_content(c0, cw))), 0

        t_global = 0.0
        n_scenes = len(data)
        for si, (card, weight, w_scene) in enumerate(data):
            t_scene = total_dur * weight
            scene_start_t = t_global
            scene_end_t = t_global + t_scene
            left = widget_left_x_in_content(card, cw)
            shots = card.shot_widgets

            if not shots:
                if (scene_start_t <= timeline_position < scene_end_t) or (
                    si == n_scenes - 1 and timeline_position >= scene_start_t
                ):
                    frac = (timeline_position - scene_start_t) / t_scene if t_scene > 0 else 0.0
                    frac = max(0.0, min(1.0, frac))
                    x = left + frac * w_scene
                    return int(round(x)), 0
                t_global = scene_end_t
                continue

            shot_ws = [float(sh.width()) for sh in shots]
            sw = sum(shot_ws)
            if sw <= 0:
                t_global = scene_end_t
                continue
            t_shots = [t_scene * (swi / sw) for swi in shot_ws]
            shot_lefts = [widget_left_x_in_content(sh, cw) for sh in shots]

            t_local = scene_start_t
            ns = len(shots)
            for j, sh in enumerate(shots):
                td = t_shots[j]
                te = t_local + td
                is_last = si == n_scenes - 1 and j == ns - 1
                if (t_local <= timeline_position < te) or (is_last and timeline_position >= t_local):
                    time_in = timeline_position - t_local
                    if td > 0:
                        time_in = min(max(time_in, 0.0), td)
                    frac = time_in / td if td > 0 else 0.0
                    sl = shot_lefts[j]
                    x = sl + frac * shot_ws[j]
                    return int(round(x)), 0
                t_local = te
            t_global = scene_end_t

        last_card, _w, w_last = data[-1]
        lx = widget_left_x_in_content(last_card, cw)
        return int(round(lx + w_last)), 0

    def _sync_selection_for_timeline_position(self, timeline_position: float) -> None:
        self._ensure_secondary_timelines_loaded()
        mode = self._effective_timeline_mode()
        project = self.workspace.get_project()
        if not project:
            return
        if mode == "video":
            _, card_number = self.calculate_timeline_x(timeline_position)
            if card_number > 0:
                project.get_timeline().set_item_index(card_number)
        elif mode == "script" and self.script_timeline and self.script_timeline.cards:
            _, scene_ord = self._calculate_timeline_x_script(timeline_position, project)
            if 1 <= scene_ord <= len(self.script_timeline.cards):
                self.script_timeline.select_scene(
                    self.script_timeline.cards[scene_ord - 1].scene_id
                )
        elif mode == "storyboard" and self.story_board_timeline:
            cx, _ = self._calculate_timeline_x_storyboard(timeline_position, project)
            self._select_storyboard_at_content_x(float(cx))

    def _select_storyboard_at_content_x(self, content_x: float) -> None:
        st = self.story_board_timeline
        if st:
            st.select_at_content_x(content_x)

    def _select_script_at_content_x(self, content_x: float, project) -> None:
        st = self.script_timeline
        if not st or not st.cards:
            return
        cw = st.content_widget
        durs = self._script_segment_durations(project)
        if not durs or len(durs) != len(st.cards):
            return
        n = len(st.cards)
        for i, card in enumerate(st.cards):
            left = float(card.mapTo(cw, QPoint(0, 0)).x())
            w = float(card.width())
            next_left = (
                float(st.cards[i + 1].mapTo(cw, QPoint(0, 0)).x()) if i + 1 < n else left + w
            )
            if left <= content_x < next_left or (i == n - 1 and left <= content_x <= left + w):
                self.script_timeline.select_scene(card.scene_id)
                return

    def get_timeline_content_width(self) -> int:
        """
        Unified scroll width: max of video-strip and screenplay-strip (same card geometry).
        """
        vcount = len(self.video_timeline.cards) if hasattr(self.video_timeline, "cards") else 0
        w = self._width_for_horizontal_cards(vcount)
        if self._secondary_timelines_loaded and self.script_timeline and hasattr(
            self.script_timeline, "cards"
        ):
            scount = len(self.script_timeline.cards)
            w = max(w, self._width_for_horizontal_cards(scount))
        if self._secondary_timelines_loaded and self.story_board_timeline and hasattr(
            self.story_board_timeline, "compute_content_width"
        ):
            w = max(w, self.story_board_timeline.compute_content_width())
        return w
    
    def eventFilter(self, watched, event):
        """Filter events from all child widgets to handle timeline position clicks"""
        if event.type() == QEvent.Type.MouseButtonPress:
            mouse_event = event
            if isinstance(mouse_event, QMouseEvent) and mouse_event.button() == Qt.MouseButton.LeftButton:
                # Prevent duplicate processing of the same event
                # Only process spontaneous events (from actual user input, not propagated)
                if not event.spontaneous():
                    return super().eventFilter(watched, event)
                
                # Check if this is the same event we just processed
                if self._last_click_event == event:
                    return super().eventFilter(watched, event)
                
                # Mark this event as processed
                self._last_click_event = event
                
                # Map the click position to container coordinates
                container_pos = watched.mapTo(self, mouse_event.pos())
                
                timeline_position, _ = self.calculate_timeline_position(container_pos)
                
                # Update the timeline position in project
                # Boundary validation (< 0 or > duration) is handled in set_timeline_position
                project = self.workspace.get_project()
                if project:
                    project.set_timeline_position(timeline_position)
                    self._ensure_secondary_timelines_loaded()
                    mode = self._effective_timeline_mode()
                    cx = self._container_point_to_content_x(container_pos, mode)
                    if mode == "script" and self.script_timeline and self.script_timeline.cards:
                        self._select_script_at_content_x(cx, project)
                    elif mode == "storyboard" and self.story_board_timeline:
                        self._select_storyboard_at_content_x(cx)
                    Signals().send(Signals.TIMELINE_POSITION_CLICKED, params=timeline_position)
                
                # Don't consume the event - let child widgets handle it for their own logic
                # This allows cards to be selected, subtitle/voiceover cards to be dragged, etc.
        
        # Pass the event to the base class for normal processing
        return super().eventFilter(watched, event)

    def on_timeline_position(self, timeline_position):
        timeline_x, card_index = self.calculate_timeline_x(timeline_position)
        # Get current scroll offset
        scroll_offset = self.video_timeline.scroll_area.horizontalScrollBar().value()
        self.timeline_position_overlay.on_timeline_position(timeline_position, timeline_x, scroll_offset)
    
    def _on_timeline_position_clicked_for_selection(self, sender, params=None, **kwargs):
        """Video timeline index from scrub time; script/storyboard use pixel hit-test in eventFilter."""
        if params is None:
            return
        try:
            timeline_position = float(params)
        except (TypeError, ValueError):
            return
        self._ensure_secondary_timelines_loaded()
        if self._effective_timeline_mode() != "video":
            return
        _, card_number = self.calculate_timeline_x(timeline_position)
        if card_number > 0:
            self.workspace.get_project().get_timeline().set_item_index(card_number)

    def _on_timeline_position_stopped_for_selection(self, sender, params=None, **kwargs):
        if params is None:
            return
        try:
            timeline_position = float(params)
        except (TypeError, ValueError):
            return
        self._sync_selection_for_timeline_position(timeline_position)

    def calculate_timeline_position(self, container_point: QPoint) -> Tuple[float, int]:
        """
        Map a click in this container to a playback time and a legacy index (video mode only).

        Uses the active timeline row (video / script / storyboard) and real widget geometry.
        """
        project = self.workspace.get_project()
        if not project:
            return 0.0, 0
        timeline_data = project.get_timeline()
        if not timeline_data:
            return 0.0, 0

        mode = self._effective_timeline_mode()
        content_x = self._container_point_to_content_x(container_point, mode)

        if mode == "video":
            if not self.video_timeline.cards:
                return 0.0, 0
            return self._calculate_timeline_position_video(content_x, project)

        self._ensure_secondary_timelines_loaded()
        if mode == "script":
            if not self.script_timeline or not self.script_timeline.cards:
                return 0.0, 0
            t, scene_ord = self._calculate_timeline_position_script(content_x, project)
            return t, scene_ord
        if mode == "storyboard":
            if not self.story_board_timeline:
                return 0.0, 0
            t, _ = self._calculate_timeline_position_storyboard(content_x, project)
            return t, 0
        return 0.0, 0

    def calculate_timeline_x(self, timeline_position: float) -> Tuple[int, int]:
        """
        Playback time -> playhead X in scroll content coordinates, plus video card index when applicable.
        """
        project = self.workspace.get_project()
        if not project:
            return 0, 0
        timeline_data = project.get_timeline()
        if not timeline_data:
            return 0, 0

        mode = self._effective_timeline_mode()
        if mode == "video":
            if not self.video_timeline.cards:
                return 0, 0
            return self._calculate_timeline_x_video(timeline_position, project)

        self._ensure_secondary_timelines_loaded()
        if mode == "script" and self.script_timeline and self.script_timeline.cards:
            return self._calculate_timeline_x_script(timeline_position, project)
        if mode == "storyboard" and self.story_board_timeline:
            return self._calculate_timeline_x_storyboard(timeline_position, project)
        return 0, 0

    def _update_divider_positions(self):
        """Draw dividers between subtitle / video / voice when the merged video stack is visible."""
        if (
            not self._secondary_timelines_loaded
            or self._timeline_mode != "video"
            or not self.subtitle_timeline
            or not self.voice_timeline
        ):
            self.divider_overlay.set_divider_positions(0, 0)
            return
        if self.subtitle_timeline.isHidden() or self.video_timeline.isHidden():
            self.divider_overlay.set_divider_positions(0, 0)
            return
        subtitle_height = self.subtitle_timeline.height()
        voiceover_top = self.height() - self.voice_timeline.height()
        self.divider_overlay.set_divider_positions(subtitle_height, voiceover_top)
    
    def resizeEvent(self, event):
        """Update overlay size and position when container is resized"""
        super().resizeEvent(event)
        # Position overlay to cover the entire container
        self.timeline_position_overlay.setGeometry(self.rect())
        #self.cursor_overlay.setGeometry(self.rect())
        self.divider_overlay.setGeometry(self.rect())
        self._update_divider_positions()

    def event(self, event):
        """
        Override event to track mouse position globally across all child widgets.
        Using HoverMove events allows tracking even when mouse is over cards.
        """
        event_type = event.type()
        
        if event_type == QEvent.Type.HoverMove:
            # Track mouse position anywhere in the container (including over cards)
            hover_event = event
            if isinstance(hover_event, QHoverEvent):
                pos = hover_event.position().toPoint()
                self.timeline_position_overlay.set_cursor_position(pos.x())
        elif event_type == QEvent.Type.HoverEnter:
            # Mouse entered the container
            pos = event.position().toPoint()
            self.timeline_position_overlay.set_cursor_position(pos.x())
            
        elif event_type == QEvent.Type.HoverLeave:
            self.timeline_position_overlay.clear_cursor()
            
        elif event_type == QEvent.Type.Leave:
            self.timeline_position_overlay.clear_cursor()
            
        return super().event(event)