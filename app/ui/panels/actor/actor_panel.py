"""Character panel for role/actor management."""

import logging
import os
import traceback
from typing import List, Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QFrame, QLabel,
    QPushButton, QMessageBox, QMenu, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QCursor, QPixmap
from app.ui.panels.base_panel import BasePanel
from app.ui.panels.actor.actor_edit_dialog import ActorEditDialog
from app.ui.panels.actor.actor_card import ActorCard
from app.data.character import Character, CharacterManager
from app.data.workspace import Workspace
from app.ui.worker.worker import run_in_background
from utils.thread_utils import ThreadSafetyMixin, run_safe_background_task
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class ActorPanel(ThreadSafetyMixin, BasePanel):
    """Panel for role/actor management."""

    character_selected = Signal(str)  # character_name

    def __init__(self, workspace: Workspace, parent=None):
        """Initialize the actor panel."""
        import time
        init_start = time.time()
        # Initialize ThreadSafetyMixin first
        ThreadSafetyMixin.__init__(self)
        # Then initialize BasePanel
        BasePanel.__init__(self, workspace, parent)
        self.character_manager: Optional[CharacterManager] = None
        self._character_cards: List[ActorCard] = []
        self._character_dict: dict[str, ActorCard] = {}  # character_name -> card
        init_time = (time.time() - init_start) * 1000
        logger.debug(f"⏱️  [CharacterPanel] __init__ completed in {init_time:.2f}ms")
    
    def setup_ui(self):
        """Set up the UI components with grid layout."""
        import time
        setup_start = time.time()
        self.set_panel_title(tr("Characters"))

        # Add buttons to unified toolbar
        self.add_toolbar_button("\ue610", self._on_add_character, tr("New Character"))
        self.add_toolbar_button("\ue6a7", self._on_draw_character, tr("Random Generate"))
        self.add_toolbar_button("\ue653", self._on_extract_character, tr("Extract From Story"))

        # Scroll area for actor grid (like file manager)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)  # Allow container to resize based on content
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Ensure content aligns to top-left
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background: #3c3f41;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #606060;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #707070;
            }
        """)

        # Container for grid layout (2 columns)
        # Similar to file manager icon view: fixed icon size, uniform spacing, auto-wrap
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: #1e1e1e;")
        # Size policy: preferred horizontally (fit content), minimum vertically (content-based height)
        # This ensures container doesn't stretch unnecessarily
        self.grid_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self.grid_layout = QGridLayout(self.grid_container)
        # Margins: 10px on all sides for consistent spacing (like file manager)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        # Spacing: 10px between cards (both horizontal and vertical, uniform like file manager)
        self.grid_layout.setSpacing(10)
        # Don't stretch columns - columns size based on fixed card width (85px + spacing)
        self.grid_layout.setColumnStretch(0, 0)
        self.grid_layout.setColumnStretch(1, 0)
        # Set column minimum width to ensure proper spacing
        self.grid_layout.setColumnMinimumWidth(0, 0)
        self.grid_layout.setColumnMinimumWidth(1, 0)
        # Don't stretch rows - rows size based on fixed card height (85px + spacing)
        # Alignment: top-left, like file manager icon view
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll_area.setWidget(self.grid_container)
        self.content_layout.addWidget(scroll_area, 1)

        setup_time = (time.time() - setup_start) * 1000
        logger.debug(f"⏱️  [CharacterPanel] setup_ui completed in {setup_time:.2f}ms")

        # Character manager will be loaded in load_data()
        # Data loading is deferred until panel activation
        # But if panel is already visible/active, start loading immediately
        if self._is_active or self.isVisible():
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._perform_initial_load)
        else:
            # If panel is not active/visible yet, ensure loading happens when it becomes active
            # This is the main activation path, but we also want to handle potential visibility changes
            from PySide6.QtCore import QTimer
            # Schedule a check after the UI is fully set up to see if the panel has become visible
            QTimer.singleShot(100, self._check_and_load_if_visible)

    def _check_and_load_if_visible(self):
        """Check if panel is visible and trigger loading if needed"""
        if self._is_active or self.isVisible():
            if not self._data_loaded and not self._is_loading:
                self._perform_initial_load()
    
    def resizeEvent(self, event):
        """Handle resize event - update layout like file manager"""
        super().resizeEvent(event)
        # Cards are fixed size, container adjusts naturally
        if hasattr(self, 'grid_container'):
            self.grid_container.adjustSize()
    
    def _connect_signals(self):
        """Connect actor manager signals"""
        if self.character_manager:
            # Disconnect first to avoid duplicate connections
            try:
                self.character_manager.character_added.disconnect(self._on_character_added)
                self.character_manager.character_updated.disconnect(self._on_character_updated)
                self.character_manager.character_deleted.disconnect(self._on_character_deleted)
            except:
                pass  # Ignore if not connected
            
            # Connect signals
            self.character_manager.character_added.connect(self._on_character_added)
            self.character_manager.character_updated.connect(self._on_character_updated)
            self.character_manager.character_deleted.connect(self._on_character_deleted)
    
    def _load_character_manager(self):
        """Load actor manager from project (for use in on_activated)"""
        project = self.workspace.get_project()
        if project:
            self.character_manager = project.get_character_manager()
    
    def _ensure_character_manager(self) -> bool:
        """Ensure actor manager is loaded, show loading if needed

        Returns:
            True if actor manager is available, False otherwise
        """
        if self.character_manager:
            return True

        # If data is not loaded yet, trigger loading
        if not self._data_loaded:
            # Show loading state
            self.show_loading(tr("正在加载角色管理器..."))
            # Trigger loading
            self._perform_initial_load()
            # Return True to allow the operation to proceed,
            # but the actual operation will be delayed until loading completes
            return True

        # If data was loaded but manager is None, it means loading failed
        QMessageBox.warning(self, tr("错误"), tr("角色管理器未初始化，请检查项目配置"))
        return False
    
    def _on_add_character(self):
        """Handle add actor button click"""
        # If actor manager is not available, try to load it
        if not self.character_manager:
            # If data is not loaded yet, trigger loading
            if not self._data_loaded:
                self.show_loading(tr("正在加载角色管理器..."))
                self._perform_initial_load()
                # Show a message to the user that loading is in progress
                QMessageBox.information(self, tr("提示"), tr("角色管理器正在后台加载，请稍后再试添加角色"))
                return
            else:
                # If data was loaded but manager is None, it means loading failed
                QMessageBox.warning(self, tr("错误"), tr("角色管理器未初始化，请检查项目配置"))
                return

        dialog = ActorEditDialog(self.character_manager, parent=self)
        dialog.character_saved.connect(self._on_character_saved)
        dialog.exec()
    
    def _on_draw_character(self):
        """Handle draw actor button click (抽卡)"""
        # If actor manager is not available, try to load it
        if not self.character_manager:
            # If data is not loaded yet, trigger loading
            if not self._data_loaded:
                self.show_loading(tr("正在加载角色管理器..."))
                self._perform_initial_load()
                # Show a message to the user that loading is in progress
                QMessageBox.information(self, tr("提示"), tr("角色管理器正在后台加载，请稍后再试随机生成角色"))
                return
            else:
                # If data was loaded but manager is None, it means loading failed
                QMessageBox.warning(self, tr("错误"), tr("角色管理器未初始化，请检查项目配置"))
                return
        # TODO: Implement actor drawing feature
        QMessageBox.information(self, tr("提示"), tr("抽卡功能开发中..."))
    
    def _on_extract_character(self):
        """Handle extract actor button click (提取)"""
        # If actor manager is not available, try to load it
        if not self.character_manager:
            # If data is not loaded yet, trigger loading
            if not self._data_loaded:
                self.show_loading(tr("正在加载角色管理器..."))
                self._perform_initial_load()
                # Show a message to the user that loading is in progress
                QMessageBox.information(self, tr("提示"), tr("角色管理器正在后台加载，请稍后再试提取角色"))
                return
            else:
                # If data was loaded but manager is None, it means loading failed
                QMessageBox.warning(self, tr("错误"), tr("角色管理器未初始化，请检查项目配置"))
                return
        # TODO: Implement actor extraction feature
        QMessageBox.information(self, tr("提示"), tr("提取功能开发中..."))
    
    def _on_character_clicked(self, character_name: str):
        """Handle actor card click - for selection only"""
        self.character_selected.emit(character_name)

    def _on_character_selection_changed(self, character_name: str, is_selected: bool):
        """Handle actor selection state change"""
        # This can be used to maintain selection state or perform other actions
        # For now, we just emit the selection signal
        if is_selected:
            self.character_selected.emit(character_name)
    
    def _on_edit_character(self, character_name: str):
        """Handle edit actor request"""
        if not self.character_manager:
            # If data is not loaded yet, trigger loading
            if not self._data_loaded:
                self.show_loading(tr("正在加载角色管理器..."))
                self._perform_initial_load()
                # Show a message to the user that loading is in progress
                QMessageBox.information(self, tr("提示"), tr("角色管理器正在后台加载，请稍后再试编辑角色"))
                return
            else:
                # If data was loaded but manager is None, it means loading failed
                QMessageBox.warning(self, tr("错误"), tr("角色管理器未初始化，请检查项目配置"))
                return

        dialog = ActorEditDialog(self.character_manager, character_name, parent=self)
        dialog.character_saved.connect(self._on_character_saved)
        dialog.exec()
    
    
    def _load_characters(self):
        """Load characters from CharacterManager synchronously"""
        if not self.character_manager:
            return
        
        # Ensure UI components are initialized
        if not hasattr(self, 'grid_layout'):
            return
        
        # Stop any ongoing batch process
        if hasattr(self, '_pending_characters'):
            self._pending_characters = []
        
        # Ensure _character_cards is initialized
        if not hasattr(self, '_character_cards'):
            self._character_cards = []
        if not hasattr(self, '_character_dict'):
            self._character_dict = {}
            
        # Show loading state
        self.show_loading(tr("正在加载角色..."))
        
        # Load characters synchronously to avoid thread issues
        try:
            characters = self.character_manager.list_characters()
            self._on_characters_loaded(characters)
        except Exception as e:
            self._on_load_error(str(e), e)

    def _on_characters_loaded(self, characters: List[Character]):
        """Callback when characters are loaded from background thread"""
        # Ensure UI components are still valid (panel might have been closed/switched)
        if not hasattr(self, 'grid_layout'):
            self.hide_loading()
            return
            
        # Clear existing cards asynchronously to avoid blocking
        if self._character_cards:
            for card in self._character_cards:
                self.grid_layout.removeWidget(card)
                card.deleteLater()
            self._character_cards.clear()
            self._character_dict.clear()
            # Process events to allow deletion to complete before creating new cards
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
        
        if not characters:
            self.hide_loading()
            return

        # Start batch creation of cards to avoid blocking UI thread
        # Process one card at a time with minimal delay between cards
        self._pending_characters = characters.copy()
        self._batch_row = 0
        self._batch_col = 0
        # Start processing with a small delay to ensure UI is ready
        QTimer.singleShot(10, self._process_next_batch)

    def _process_next_batch(self):
        """Process a batch of actor cards to keep UI responsive"""
        if not hasattr(self, '_pending_characters') or not self._pending_characters:
            self.grid_container.adjustSize()
            self.hide_loading() # Hide loading once all cards are created
            return

        # Process only 1 card at a time to ensure UI stays responsive
        # This prevents any blocking from card creation or layout operations
        character = self._pending_characters.pop(0)
        
        # Create card (fast - no image loading in __init__)
        card = ActorCard(character, self)
        card.edit_requested.connect(self._on_edit_character)
        card.clicked.connect(self._on_character_clicked)
        card.selection_changed.connect(self._on_character_selection_changed)

        self.grid_layout.addWidget(
            card,
            self._batch_row,
            self._batch_col,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.grid_layout.setRowStretch(self._batch_row, 0)
        self.grid_layout.setColumnMinimumWidth(self._batch_col, 0)

        self._character_cards.append(card)
        self._character_dict[character.name] = card

        # Move to next position (2 columns)
        self._batch_col += 1
        if self._batch_col >= 2:
            self._batch_col = 0
            self._batch_row += 1

        # Schedule next card with a small delay to allow UI event loop to process
        # This ensures mouse/keyboard events are handled and UI stays responsive
        # Using 10ms delay balances responsiveness with loading speed
        QTimer.singleShot(10, self._process_next_batch)

    def _on_load_error(self, error_msg: str, exception: Exception):
        """Handle loading error"""
        logger.error(f"❌ Error loading actor manager: {error_msg}")
        logger.error(f"Exception: {exception}", exc_info=True)

        # Don't mark as loaded immediately - allow for retry in certain cases
        if not hasattr(self, '_load_attempts'):
            self._load_attempts = 0

        self._load_attempts += 1

        if self._load_attempts < 3:  # Retry up to 3 times
            logger.info(f"Retrying actor manager load (attempt {self._load_attempts + 1})...")
            from PySide6.QtCore import QTimer
            # Retry after a short delay
            QTimer.singleShot(1000, self._perform_initial_load)  # 1 second delay before retry
        else:
            logger.error("Max retries reached, giving up on actor manager loading")
            # Mark as loaded to avoid infinite retries
            self._data_loaded = True
            self.hide_loading()

    def _on_character_saved(self, character_name: str):
        """Handle actor saved signal"""
        self._load_characters()
    
    def _on_character_added(self, character: Character):
        """Handle actor added signal"""
        self._load_characters()
    
    def _on_character_updated(self, character: Character):
        """Handle actor updated signal"""
        # Reload all characters to ensure consistency
        self._load_characters()
    
    def _on_character_deleted(self, character_name: str):
        """Handle actor deleted signal"""
        # Reload all characters
        self._load_characters()
    
    def _perform_initial_load(self):
        """Override to prevent setting _data_loaded before async loading completes"""
        if not self._data_loaded:
            self.load_data()
            # Don't set _data_loaded here - it will be set in _on_character_manager_loaded
    
    def load_data(self):
        """Load actor data when panel is first activated."""
        # Get project - this should be fast if workspace is already initialized
        # But if workspace initialization is deferred, this might trigger it
        # So we defer this to background thread

        def _load_character_manager():
            """Load actor manager in background to avoid blocking"""
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    project = self.workspace.get_project()
                    if project:
                        # Ensure project is fully initialized before accessing actor manager
                        # The actor manager should always exist, but its data might not be loaded yet
                        char_manager = project.get_character_manager()
                        logger.info(f"Character manager retrieved (attempt {retry_count + 1}): {char_manager is not None}")

                        # Additional check: try to access some data to ensure it's ready
                        if char_manager:
                            # This will trigger the loading if not already loaded
                            char_count = len(char_manager.list_characters())
                            logger.info(f"Character manager has {char_count} characters")

                        return char_manager
                    else:
                        logger.warning(f"Project not available when loading actor manager (attempt {retry_count + 1})")
                        if retry_count < max_retries - 1:
                            import time
                            time.sleep(0.5)  # Wait before retry
                            retry_count += 1
                        else:
                            return None
                except Exception as e:
                    logger.error(f"Error loading actor manager (attempt {retry_count + 1}): {e}", exc_info=True)
                    if retry_count < max_retries - 1:
                        import time
                        time.sleep(0.5)  # Wait before retry
                        retry_count += 1
                    else:
                        logger.error(f"Failed to load actor manager after {max_retries} attempts")
                        raise  # Re-raise to be caught by the worker

        # Show loading indicator while waiting for actor manager
        self.show_loading(tr("正在加载角色管理器..."))

        logger.info("Starting background loading of actor manager...")

        # Use the safe background task runner that handles object validity
        self.safe_run_in_background(
            _load_character_manager,
            on_finished=self._on_character_manager_loaded,
            on_error=self._on_load_error
        )
    
    def _on_character_manager_loaded(self, character_manager):
        """Callback when actor manager is loaded"""
        logger.info(f"✅ Character manager loaded callback called with manager: {character_manager is not None}")

        if character_manager:
            self.character_manager = character_manager
            logger.info(f"Character manager assigned: {self.character_manager is not None}")
            # Connect signals after manager is loaded
            self._connect_signals()
            logger.info("Signals connected")
            # Mark data as loaded only after manager is successfully loaded
            self._data_loaded = True
            logger.info("Data marked as loaded")
            # Load characters
            self._load_characters()
            logger.info("Characters loading initiated")
        else:
            logger.warning("Character manager is None, marking as loaded to avoid retries")
            # If loading failed, still mark as loaded to avoid infinite retries
            self._data_loaded = True
            self.hide_loading()
    
    def on_activated(self):
        """Called when panel becomes visible."""
        super().on_activated()
        # Reload characters when panel is activated (refresh data)
        # Only reload if data was already loaded (i.e., not the first activation)
        if self._data_loaded and self.character_manager:
            self._connect_signals()
            self._load_characters()
        # If _data_loaded is False, load_data() will be called by base class
        logger.info("✅ Character panel activated")
    
    def on_deactivated(self):
        """Called when panel is hidden."""
        # Use the ThreadSafetyMixin's cleanup method
        self.cleanup_workers_on_deactivate()

        super().on_deactivated()
        logger.info("⏸️ Character panel deactivated")
    
    def on_project_switched(self, project_name: str):
        """Handle project switch"""
        # Reset data loaded state to trigger reload
        self._data_loaded = False
        # Clear existing actor manager
        self.character_manager = None
        # Call super to trigger reload if panel is active
        super().on_project_switched(project_name)

    def closeEvent(self, event):
        """Handle close event to properly cleanup resources"""
        # Stop any running background workers to prevent segfaults
        if hasattr(self, '_character_manager_worker'):
            try:
                if self._character_manager_worker and self._character_manager_worker.is_running():
                    self._character_manager_worker.stop()
            except:
                pass  # Ignore errors when stopping worker
            self._character_manager_worker = None

        super().closeEvent(event)

