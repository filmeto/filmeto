from .base_timeline_scroll import BaseTimelineScroll


class ScreenplayTimelineScroll(BaseTimelineScroll):
    """Horizontal scroll area for screenplay scene cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screenplay_timeline_scroll")
