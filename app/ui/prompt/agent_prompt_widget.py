"""QML-based common agent prompt input widget with lightweight context chips."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr


AGENT_PROMPT_QML_PATH = Path(__file__).resolve().parent.parent / "qml" / "prompt" / "AgentPromptWidget.qml"


class _AgentPromptBridge(QObject):
    textChanged = Signal()
    enabledChanged = Signal()
    placeholderChanged = Signal()
    sendLabelChanged = Signal()
    contextsChanged = Signal()
    conversationActiveChanged = Signal()
    submitted = Signal(str)
    addContextRequested = Signal()
    contextRemoveRequested = Signal(str)
    cancelRequested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._text = ""
        self._enabled = True
        self._placeholder = tr("Input Prompts...")
        self._send_label = tr("Send")
        self._contexts: list[dict[str, str]] = []
        self._conversation_active = False

    @Property(str, notify=textChanged)
    def text(self) -> str:
        return self._text

    @Property(bool, notify=enabledChanged)
    def enabled(self) -> bool:
        return self._enabled

    @Property(str, notify=placeholderChanged)
    def placeholder(self) -> str:
        return self._placeholder

    @Property(str, notify=sendLabelChanged)
    def sendLabel(self) -> str:
        return self._send_label

    @Property("QVariantList", notify=contextsChanged)
    def contexts(self) -> list[dict[str, str]]:
        return self._contexts

    @Property(bool, notify=conversationActiveChanged)
    def conversationActive(self) -> bool:
        return self._conversation_active

    @Slot(str)
    def on_text_changed(self, value: str):
        if self._text != value:
            self._text = value
            self.textChanged.emit()

    @Slot()
    def submit(self):
        message = (self._text or "").strip()
        if not message or not self._enabled:
            return
        self.submitted.emit(message)
        self._text = ""
        self.textChanged.emit()

    @Slot()
    def request_add_context(self):
        self.addContextRequested.emit()

    @Slot(str)
    def request_remove_context(self, context_id: str):
        self.contextRemoveRequested.emit(context_id)

    @Slot()
    def request_cancel(self):
        self.cancelRequested.emit()

    def set_enabled(self, enabled: bool):
        if self._enabled != enabled:
            self._enabled = enabled
            self.enabledChanged.emit()

    def set_placeholder(self, text: str):
        text = text or ""
        if self._placeholder != text:
            self._placeholder = text
            self.placeholderChanged.emit()

    def set_text(self, text: str):
        text = text or ""
        if self._text != text:
            self._text = text
            self.textChanged.emit()

    def set_contexts(self, contexts: list[dict[str, str]]):
        self._contexts = contexts
        self.contextsChanged.emit()

    def set_conversation_active(self, active: bool):
        if self._conversation_active != active:
            self._conversation_active = active
            self.conversationActiveChanged.emit()


class AgentPromptWidget(BaseWidget):
    prompt_submitted = Signal(str)
    message_submitted = Signal(str)
    add_context_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self._contexts: list[dict[str, str]] = []
        self._bridge = _AgentPromptBridge(self)
        self._bridge.submitted.connect(self.prompt_submitted.emit)
        self._bridge.addContextRequested.connect(self.add_context_requested.emit)
        self._bridge.contextRemoveRequested.connect(self.remove_context_item)
        self._bridge.cancelRequested.connect(self.cancel_requested.emit)
        self.prompt_submitted.connect(self.message_submitted.emit)

        self._quick = QQuickWidget(self)
        self._quick.setObjectName("agent_prompt_widget")
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        # Keep the prompt widget surface opaque so it matches its QML background.
        self._quick.setAttribute(Qt.WA_TranslucentBackground, False)
        self._quick.setClearColor(QColor("#2b2d30"))
        self._quick.rootContext().setContextProperty("agentPromptBridge", self._bridge)
        self._quick.setSource(QUrl.fromLocalFile(str(AGENT_PROMPT_QML_PATH)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._quick)

    def get_text(self) -> str:
        return self._bridge.text

    def set_text(self, text: str):
        self._bridge.set_text(text)

    def clear(self):
        self._bridge.set_text("")

    def set_enabled(self, enabled: bool):
        self._bridge.set_enabled(enabled)

    def set_placeholder(self, text: str):
        self._bridge.set_placeholder(text)

    def set_conversation_active(self, active: bool):
        self._bridge.set_conversation_active(active)

    def add_context_item(self, context_id: str, context_name: str):
        for item in self._contexts:
            if item.get("id") == context_id:
                return
        self._contexts.append({"id": context_id, "name": context_name})
        self._bridge.set_contexts(list(self._contexts))

    @Slot(str)
    def remove_context_item(self, context_id: str):
        before = len(self._contexts)
        self._contexts = [item for item in self._contexts if item.get("id") != context_id]
        if len(self._contexts) != before:
            self._bridge.set_contexts(list(self._contexts))

    def clear_context_items(self):
        self._contexts.clear()
        self._bridge.set_contexts([])

    def get_context_items(self):
        return [item.get("id", "") for item in self._contexts]
