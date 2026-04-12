from .base_timeline_scroll import BaseTimelineScroll


class StoryBoardTimelineScroll(BaseTimelineScroll):
    """Horizontal scroll for storyboard scene strips."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("story_board_timeline_scroll")
