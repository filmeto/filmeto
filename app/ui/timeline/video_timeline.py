import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout,
    QLabel, QVBoxLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QPixmap

from app.data.timeline import TimelineItem
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget, BaseTaskWidget
from app.ui.timeline.video_timeline_scroll import VideoTimelineScroll
from app.ui.timeline.video_timeline_card import VideoTimelineCard
from utils import qt_utils
from utils.i18n_utils import tr, translation_manager

logger = logging.getLogger(__name__)


class AddCardFrame(QFrame):
    """Special frame for adding new cards to the timeline"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        # Basic configuration
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                background-color: #2c2c2c;
                border: 2px dashed #666666;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #3c3c3c;
                border: 2px dashed #8888ff;
            }
        """)
        
        # Set initial size
        self.setMinimumSize(90, 160)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Enable mouse tracking
        self.setMouseTracking(True)

        # Content layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        # Title label
        self.title_label = QLabel(tr("Add Card"))
        self.title_label.setAlignment(Qt.AlignCenter)
        font = self.title_label.font()
        font.setPointSize(10)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.title_label)

        # Set cursor to indicate clickable
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        """Handle mouse click event to add a new card"""
        if event.button() == Qt.LeftButton:
            if hasattr(self.parent, 'add_new_card'):
                self.parent.add_new_card()


class VideoTimeline(BaseTaskWidget):
    """左右滑动的卡片式时间线主窗口"""
    def __init__(self,parent:QWidget,workspace:Workspace):
        super().__init__(workspace)
        self.setWindowTitle(tr("TimeLine"))
        self.resize(parent.width(), parent.height())
        self.setContentsMargins(0, 0, 0, 0)  # Remove widget margins, use layout margins instead
        self.selected_card_index = None  # 跟踪当前选中的卡片索引
        
        # Set fixed height to accommodate cards (160px) + layout margins (5px top + 5px bottom)
        self.setFixedHeight(170)
        # Set size policy to prevent vertical expansion
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # ------------------- 创建可滚动区域 -------------------
        self.scroll_area = VideoTimelineScroll()
        self.scroll_area.setWidgetResizable(True) # 内容 widget 可随区域大小调整
        self.scroll_area.setStyleSheet(f"""
            VideoTimelineScroll {{
                background-color: #1e1f22;
            }}
        """)
        # ------------------- 创建内容容器和布局 -------------------
        self.content_widget = BaseWidget(workspace)
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #1e1f22;
            }}
        """)
        self.timeline_layout = QHBoxLayout(self.content_widget)
        self.timeline_layout.setContentsMargins(5, 5, 5, 5) # 左右留出边距，方便滑动
        self.timeline_layout.setSpacing(5) # 卡片之间的间距
        # 将内容容器放入滚动区域
        self.scroll_area.setWidget(self.content_widget)

        # ------------------- 添加卡片 (延迟加载图像) -------------------
        timeline = workspace.get_project().get_timeline()
        timeline_item_count = timeline.get_item_count()
        self.cards = []
        self._timeline = timeline  # 保存 timeline 引用用于延迟加载
        self._loaded_card_indices = set()  # 跟踪已加载的卡片

        for i in range(timeline_item_count):
            index = i + 1
            title = f"# {i+1}"
            # 初始创建卡片时不加载图像 (传入 None)
            # 图像将在后续按需加载
            card = VideoTimelineCard(self, title, None, index)
            self.timeline_layout.addWidget(card)
            self.cards.append(card)

        # Set the timeline to the current index from project config instead of always jumping to 1
        current_index = workspace.get_project().get_timeline_index()
        if 1 <= current_index <= timeline_item_count:
            timeline.set_item_index(current_index)
            self.selected_card_index = current_index
            # 设置当前选中的卡片为选中状态
            if self.cards:
                self.cards[current_index - 1].set_selected(True)
        else:
            # If current index is out of bounds, default to 1
            timeline.set_item_index(1)
            self.selected_card_index = 1
            if self.cards:
                self.cards[0].set_selected(True)

        # Add the "Add Card" button at the end
        self.add_card_button = AddCardFrame(self)
        self.timeline_layout.addWidget(self.add_card_button)

        self.timeline_layout.addStretch()
        # ------------------- 主窗口布局 -------------------
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.scroll_area)

        # 聚焦以接收键盘事件
        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
        self.scroll_area.setFocus()

        # Connect to language change signal
        translation_manager.language_changed.connect(self.retranslateUi)

        # Connect timeline switch signal to update card images
        self.workspace.connect_timeline_switch(self.on_timeline_switch)

        # Connect timeline changed signal to update card images when composition completes
        timeline.connect_timeline_changed(self.on_timeline_changed)

        # 设置滚动监听，延迟加载可见区域的卡片图像
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self._scroll_debounce_timer = QTimer(self)
        self._scroll_debounce_timer.setSingleShot(True)
        self._scroll_debounce_timer.setInterval(100)
        self._scroll_debounce_timer.timeout.connect(self._load_visible_cards)

        # 延迟加载初始可见区域的卡片 (100ms 后)
        QTimer.singleShot(100, self._load_initial_cards)

    def _load_initial_cards(self):
        """加载初始可见区域的卡片（当前选中卡片优先，然后向两侧扩展）"""
        if not hasattr(self, '_timeline') or not self.cards:
            return

        # 首先加载当前选中的卡片
        if self.selected_card_index and 1 <= self.selected_card_index <= len(self.cards):
            self._load_card_image(self.selected_card_index - 1)

        # 然后加载当前选中卡片附近的卡片（左右各3个）
        if self.selected_card_index:
            for offset in range(1, 4):
                # 右侧
                idx = self.selected_card_index - 1 + offset
                if idx < len(self.cards):
                    self._load_card_image(idx)
                # 左侧
                idx = self.selected_card_index - 1 - offset
                if idx >= 0:
                    self._load_card_image(idx)

    def _on_scroll_changed(self):
        """滚动事件防抖处理"""
        if hasattr(self, '_scroll_debounce_timer'):
            self._scroll_debounce_timer.start()

    def _load_visible_cards(self):
        """加载滚动后可见区域的卡片"""
        if not hasattr(self, '_timeline') or not self.cards:
            return

        # 获取滚动区域的可见范围
        scroll_value = self.scroll_area.horizontalScrollBar().value()
        viewport_width = self.scroll_area.viewport().width()

        # 卡片宽度 + 间距 = 95px
        card_width = 95
        start_index = max(0, scroll_value // card_width - 1)  # 稍微提前一点开始加载
        end_index = min(len(self.cards), (scroll_value + viewport_width) // card_width + 2)  # 稍微延后结束

        # 加载可见区域内的卡片
        for i in range(start_index, end_index):
            self._load_card_image(i)

    def _load_card_image(self, card_index: int):
        """加载单个卡片的图像"""
        if card_index < 0 or card_index >= len(self.cards):
            return

        # 如果已经加载过，跳过
        if card_index in self._loaded_card_indices:
            return

        self._loaded_card_indices.add(card_index)

        try:
            # 获取 timeline item 并加载图像
            timeline_item = self._timeline.get_item(card_index + 1)
            snapshot_image = timeline_item.get_image()

            # 更新卡片图像
            card = self.cards[card_index]
            if snapshot_image is not None and not snapshot_image.isNull():
                card.setImage(snapshot_image)
        except Exception as e:
            logger.warning(f"Failed to load image for card {card_index + 1}: {e}")

    def retranslateUi(self):
        """更新所有UI文本当语言变化时"""
        self.setWindowTitle(tr("TimeLine"))
        # Update Add Card button label
        if hasattr(self, 'add_card_button') and self.add_card_button:
            self.add_card_button.title_label.setText(tr("Add Card"))
    
    def keyPressEvent(self, event: QKeyEvent):
        """重写键盘事件，支持左右方向键滑动"""
        if isinstance(event, QKeyEvent):
            scroll_bar = self.scroll_area.horizontalScrollBar()
            current_value = scroll_bar.value()

            if event.key() == Qt.Key_Left:
                # 向左滑动（值减小）
                scroll_bar.setValue(current_value - 50)
            elif event.key() == Qt.Key_Right:
                # 向右滑动（值增加）
                scroll_bar.setValue(current_value + 50)
            else:
                # 如果不是左右键，调用父类处理其他事件（如关闭窗口的 Esc）
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def on_task_finished(self, result):
        timeline_index = result.get_timeline_index()
        card = self.cards[timeline_index-1]
        image_path = result.get_image_path()
        if image_path is not None:
            original_pixmap= QPixmap(image_path)
            card.setImage(original_pixmap)
        return
    
    def add_new_card(self):
        """Add a new card to the timeline"""
        try:
            timeline = self.workspace.get_project().get_timeline()
            new_index = timeline.add_item()
            self.timeline_layout.removeWidget(self.add_card_button)
            qt_utils.remove_last_stretch(self.timeline_layout)
            # 修复：使用新索引获取时间线项，然后获取图像
            new_timeline_item = timeline.get_item(new_index)
            snapshot_image = new_timeline_item.get_image()
            title = f"# {new_index}"
            new_card = VideoTimelineCard(self, title, snapshot_image, new_index)
            
            # Add the new card
            self.timeline_layout.addWidget(new_card)
            self.cards.append(new_card)
            
            # Re-add the add button and stretch
            self.timeline_layout.addWidget(self.add_card_button)
            self.timeline_layout.addStretch()
            
            # Update the timeline index to the newly created card
            timeline.set_item_index(new_index)
            
            # Update unified scroll range for all timelines
            if hasattr(self.parent(), 'update_unified_scroll_range'):
                self.parent().update_unified_scroll_range()
            
            # Force a layout update
            self.content_widget.update()
            self.update()
            
        except Exception as e:
            logger.error(f"Error adding new card: {e}", exc_info=True)

    def on_timeline_switch(self, item: TimelineItem):
        """Handle timeline switch to update card images"""
        # Update the image for the card corresponding to the switched timeline item
        index = item.get_index()
        if 1 <= index <= len(self.cards):
            # Load the new image and update the card
            pixmap = item.get_image()
            self.cards[index-1].setImage(pixmap)

        # 取消之前选中卡片的选中状态
        if self.selected_card_index is not None and 1 <= self.selected_card_index <= len(self.cards):
            self.cards[self.selected_card_index - 1].set_selected(False)

        # 设置新选中的卡片
        self.selected_card_index = index
        if 1 <= index <= len(self.cards):
            self.cards[index - 1].set_selected(True)
    
    def on_timeline_changed(self, timeline, timeline_item: TimelineItem):
        """Handle timeline changed signal (fired when composition completes)"""
        # Update the card image for the timeline item that just completed composition
        index = timeline_item.get_index()
        if 1 <= index <= len(self.cards):
            # Reload the image (image.png has been updated)
            pixmap = timeline_item.get_image()
            self.cards[index - 1].setImage(pixmap)
            logger.info(f"Updated timeline card {index} after composition")
    
    def on_project_switched(self, project_name):
        """处理项目切换"""
        # 清除现有的卡片
        for card in self.cards:
            self.timeline_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()
        
        # 移除添加卡片按钮和占位符
        self.timeline_layout.removeWidget(self.add_card_button)
        qt_utils.remove_last_stretch(self.timeline_layout)
        
        # 重新加载新项目的时间线卡片
        timeline = self.workspace.get_project().get_timeline()
        timeline_item_count = timeline.get_item_count()
        
        for i in range(timeline_item_count):
            index = i + 1
            timeline_item = timeline.get_item(index)
            snapshot_image = timeline_item.get_image()
            title = f"# {index}"
            card = VideoTimelineCard(self, title, snapshot_image, index)
            self.timeline_layout.addWidget(card)
            self.cards.append(card)
        
        # 重新添加"添加卡片"按钮和占位符
        self.timeline_layout.addWidget(self.add_card_button)
        self.timeline_layout.addStretch()
        
        # Update unified scroll range for all timelines
        if hasattr(self.parent(), 'update_unified_scroll_range'):
            self.parent().update_unified_scroll_range()
        
        # 重置选中状态
        self.selected_card_index = None
        current_index = self.workspace.get_project().get_timeline_index()
        if 1 <= current_index <= timeline_item_count:
            timeline.set_item_index(current_index)
            self.selected_card_index = current_index
            if self.cards:
                self.cards[current_index - 1].set_selected(True)
        else:
            # 如果当前索引超出范围，默认为1
            timeline.set_item_index(1)
            self.selected_card_index = 1
            if self.cards:
                self.cards[0].set_selected(True)