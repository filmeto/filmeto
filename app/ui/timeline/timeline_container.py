"""
Timeline Container Widget

This widget provides a container for the timeline that draws a vertical cursor line
following the mouse position. The line is drawn on top of all timeline content
including cards, and mouse tracking works across all child widgets.
"""

import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QPoint, QEvent, QPointF, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QHoverEvent, QPolygonF, QMouseEvent
from typing import Tuple

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.signals import Signals
from app.ui.timeline.video_timeline import VideoTimeline
from app.ui.timeline.subtitle_timeline import SubtitleTimeline
from app.ui.timeline.voice_timeline import VoiceTimeline

logger = logging.getLogger(__name__)


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
        # Timeline card dimensions (from HoverZoomFrame)
        self.card_width = 90  # Fixed width of each card
        self.card_spacing = 5  # Spacing between cards (from timeline_layout.setSpacing(5))
        self.content_margin_left = 5  # Left margin from timeline_layout.setContentsMargins(5, 5, 5, 5)
        # Create the main timeline widget (VideoTimeline - immediately required)
        self.video_timeline = VideoTimeline(self, workspace)

        # Create placeholders for secondary timelines (lazy loaded)
        self.subtitle_timeline = None
        self.voice_timeline = None
        self._secondary_timelines_loaded = False

        # Scroll synchronization state
        self._scroll_sync_active = False  # Flag to prevent feedback loops
        self._last_scroll_position = 0  # Cache last synchronized scroll value

        # Setup the layout - only add video timeline initially
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        # Only add video timeline initially for fast display
        self.main_layout.addWidget(self.video_timeline)

        # Create the overlay widget for drawing position line
        timeline_position = self.workspace.get_project().get_timeline_position()
        timeline_x, card_index = self.calculate_timeline_x(timeline_position)
        self.timeline_position_overlay = TimelinePositionLineOverlay(self, timeline_position,timeline_x)

        # Create the overlay widget for drawing divider lines
        self.divider_overlay = TimelineDividerLinesOverlay(self)

        # Enable hover events to track mouse globally
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setMouseTracking(True)

        # Enable mouse press events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Connect to signals for card selection
        Signals().connect(Signals.TIMELINE_POSITION_CLICKED, self._on_timeline_position_signal)
        Signals().connect(Signals.TIMELINE_POSITION_STOPPED, self._on_timeline_position_signal)

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

    def _load_secondary_timelines(self):
        """Load secondary timelines (subtitle, voice) in the background after initial display"""
        if self._secondary_timelines_loaded:
            return

        self._secondary_timelines_loaded = True
        logger.info("Loading secondary timelines (subtitle, voice)...")

        # Timer to detect when scrolling has stopped (for cursor show/hide)
        self._scroll_stop_timer = QTimer(self)
        self._scroll_stop_timer.setSingleShot(True)
        self._scroll_stop_timer.setInterval(100)  # 100ms delay after scroll stops
        self._scroll_stop_timer.timeout.connect(self._on_scroll_stopped)

        # Create secondary timelines
        self.subtitle_timeline = SubtitleTimeline(self, self.workspace)
        self.voice_timeline = VoiceTimeline(self, self.workspace)

        # Install event filters for secondary timelines
        self._install_event_filters_recursively(self.subtitle_timeline)
        self._install_event_filters_recursively(self.voice_timeline)

        # Add to layout in the correct order
        self.main_layout.insertWidget(0, self.subtitle_timeline)
        self.main_layout.insertWidget(2, self.voice_timeline)

        # Setup scroll synchronization
        self.setup_scroll_synchronization()

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
        # Get scrollbars from all three timelines
        video_scrollbar = self.video_timeline.scroll_area.get_horizontal_scrollbar()
        subtitle_scrollbar = self.subtitle_timeline.scroll_area.get_horizontal_scrollbar()
        voice_scrollbar = self.voice_timeline.scroll_area.get_horizontal_scrollbar()
        
        # Connect scroll events to synchronization handler
        video_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('video', value))
        subtitle_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('subtitle', value))
        voice_scrollbar.valueChanged.connect(lambda value: self._on_scroll_value_changed('voice', value))
        
        # Connect scroll start/stop signals from scroll areas to hide/show cursor
        self.video_timeline.scroll_area.scroll_started.connect(self._on_scroll_started)
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

        # Set content width for secondary timelines if loaded
        if self._secondary_timelines_loaded:
            if self.subtitle_timeline:
                self.subtitle_timeline.set_content_width(width)
            if self.voice_timeline:
                self.voice_timeline.set_content_width(width)
    
    def get_timeline_content_width(self) -> int:
        """
        Calculate the unified content width based on video timeline cards.
        
        Returns:
            int: The minimum width for all timeline content widgets
        """
        # Get card count from video timeline
        if not hasattr(self.video_timeline, 'cards'):
            return 800  # Default minimum width
        
        card_count = len(self.video_timeline.cards)
        if card_count == 0:
            return 800  # Default minimum width
        
        # Calculate total width based on card layout
        # Formula: (card_width + spacing) × card_count + left_margin + right_margin + add_button_width + stretch
        total_width = (self.card_width + self.card_spacing) * card_count
        total_width += self.content_margin_left  # Left margin
        total_width += self.content_margin_left  # Right margin (same as left)
        total_width += 100  # Add card button width
        total_width += 100  # Extra space for comfort
        
        return total_width
    
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
                
                # Calculate timeline position and card number from the mapped X coordinate
                timeline_position, card_number = self.calculate_timeline_position(container_pos.x())
                
                # Update the timeline position in project
                # Boundary validation (< 0 or > duration) is handled in set_timeline_position
                project = self.workspace.get_project()
                if project:
                    # Set position in data layer
                    project.set_timeline_position(timeline_position)
                    
                    # Emit UI signal for UI components (like play control) to react
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
    
    def _on_timeline_position_signal(self, sender, params=None, **kwargs):
        """
        Handle TIMELINE_POSITION_CLICKED and TIMELINE_POSITION_STOPPED signals.
        Calculate card number from timeline position and trigger card selection in data layer.
        
        Args:
            sender: The signal sender
            params: Signal parameters - either:
                   - timeline_position (float) for TIMELINE_POSITION_CLICKED
                   - dict with timeline_position, timeline_x, card_number for TIMELINE_POSITION_STOPPED
            **kwargs: Additional keyword arguments
        """
        if params is None:
            return
        
        # Get timeline_position and card_number from params
        if isinstance(params, dict):
            timeline_position = params.get('timeline_position')
            card_number = params.get('card_number', None)
        else:
            # For TIMELINE_POSITION_CLICKED, params is the position directly
            timeline_position = params
            card_number = None
        
        if timeline_position is None:
            return
        
        # If card_number is not provided, calculate it from timeline_position
        if card_number is None:
            _, card_number = self.calculate_timeline_x(timeline_position)
        
        # Only set item index if card_number is valid (> 0)
        if card_number > 0:
            self.workspace.get_project().get_timeline().set_item_index(card_number)

    def calculate_timeline_position(self, mouse_x: int) -> Tuple[float, int]:
        """
        Calculate the playback position in seconds and card number based on mouse X coordinate.
        
        Args:
            mouse_x: Mouse X coordinate in the container
            
        Returns:
            tuple[float, int]: (Playback position in seconds with millisecond precision, Card number/index)
                              Card number is 1-indexed. Returns 0 if before first card or no cards exist.
        """
        # Get the timeline widget's cards
        timeline = self.video_timeline
        if not hasattr(timeline, 'cards') or not timeline.cards:
            return 0.0, 0
        
        # Get the workspace and project to access timeline items
        workspace = timeline.workspace
        if not workspace:
            return 0.0, 0
            
        project = workspace.get_project()
        if not project:
            return 0.0, 0
            
        timeline_data = project.get_timeline()
        if not timeline_data:
            return 0.0, 0
        
        # Account for scroll position
        scroll_area = timeline.scroll_area
        scroll_offset = scroll_area.horizontalScrollBar().value()
        
        # Adjust mouse position for scroll offset and left margin
        adjusted_x = mouse_x + scroll_offset - self.content_margin_left
        
        # If mouse is before the first card, position is 0
        if adjusted_x < 0:
            return 0.0, 0
        
        # Calculate which card the mouse is over and position within that card
        accumulated_time = 0.0
        current_x = 0
        
        for i, card in enumerate(timeline.cards):
            card_index = i + 1  # Cards are 1-indexed
            
            # Get duration for this card directly from project
            try:
                item_duration = project.get_item_duration(card_index)
            except Exception as e:
                logger.error(f"Error getting duration for card {card_index}: {e}")
                item_duration = 1.0  # Default to 1 second if error
            
            # Calculate card boundaries
            card_start_x = current_x
            card_end_x = current_x + self.card_width
            
            # Check if mouse is within this card
            if adjusted_x >= card_start_x and adjusted_x < card_end_x:
                # Calculate position within the card
                position_in_card = adjusted_x - card_start_x
                # Calculate time fraction within this card
                time_fraction = position_in_card / self.card_width
                # Calculate absolute time position
                position_in_seconds = accumulated_time + (time_fraction * item_duration)
                # Round to millisecond precision (3 decimal places)
                return round(position_in_seconds, 3), card_index
            
            # Move to next card
            accumulated_time += item_duration
            current_x = card_end_x + self.card_spacing
        
        # If mouse is after all cards, return the total duration and last card index
        last_card_index = len(timeline.cards)
        return round(accumulated_time, 3), last_card_index
    
    def calculate_timeline_x(self, timeline_position: float) -> Tuple[int, int]:
        """
        Calculate the X coordinate and card number based on timeline position in seconds (reverse of calculate_timeline_position).
        
        Args:
            timeline_position: Playback position in seconds
            
        Returns:
            tuple[int, int]: (X coordinate in the container, Card number/index)
                            Card number is 1-indexed. Returns 0 if before first card or no cards exist.
        """
        # Get the timeline widget's cards
        timeline = self.video_timeline
        if not hasattr(timeline, 'cards') or not timeline.cards:
            return self.content_margin_left, 0
        
        # Get the workspace and project to access timeline items
        workspace = timeline.workspace
        if not workspace:
            return self.content_margin_left, 0
            
        project = workspace.get_project()
        if not project:
            return self.content_margin_left, 0
            
        timeline_data = project.get_timeline()
        if not timeline_data:
            return self.content_margin_left, 0
        
        # If position is negative or zero, return the start position
        if timeline_position <= 0:
            return self.content_margin_left, 0
        
        # Calculate which card the position falls into
        accumulated_time = 0.0
        current_x = 0
        
        for i, card in enumerate(timeline.cards):
            card_index = i + 1  # Cards are 1-indexed
            
            # Get duration for this card directly from project
            try:
                item_duration = project.get_item_duration(card_index)
            except Exception as e:
                logger.error(f"Error getting duration for card {card_index}: {e}")
                item_duration = 1.0  # Default to 1 second if error
            
            # Calculate card boundaries in time
            card_start_time = accumulated_time
            card_end_time = accumulated_time + item_duration
            
            # Check if position falls within this card's time range
            if timeline_position >= card_start_time and timeline_position < card_end_time:
                # Calculate time offset within this card
                time_in_card = timeline_position - card_start_time
                # Calculate position fraction within this card
                time_fraction = time_in_card / item_duration if item_duration > 0 else 0
                # Calculate X position within the card
                position_in_card = time_fraction * self.card_width
                # Calculate absolute X position (before adjusting for scroll)
                adjusted_x = current_x + position_in_card
                # Convert to container coordinate (add margin, no scroll adjustment for display)
                container_x = adjusted_x + self.content_margin_left
                return int(container_x), card_index
            
            # Move to next card
            accumulated_time += item_duration
            current_x += self.card_width + self.card_spacing
        
        # If position is after all cards, return the position at the end and last card index
        final_x = current_x + self.content_margin_left
        last_card_index = len(timeline.cards)
        return int(final_x), last_card_index

    def _update_divider_positions(self):
        """Update divider line positions based on component heights"""
        subtitle_height = 0
        voiceover_top = 0
        
        if self.subtitle_timeline and not self.subtitle_timeline.isHidden():
            subtitle_height = self.subtitle_timeline.height()
            
        if self.voice_timeline and not self.voice_timeline.isHidden():
            # Calculate position of voiceover timeline
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