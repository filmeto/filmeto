"""
Global Signal Manager for UI Component Communication

This singleton class manages signals for communication between UI components,
keeping UI logic separate from the data layer.
"""
from typing import Any

from blinker import signal


class Signals:
    """
    Singleton class for managing global UI signals.
    
    Provides a centralized way for UI components to communicate without
    coupling them directly or polluting the data layer with UI-specific signals.
    """
    
    _instance = None

    TIMELINE_POSITION_CLICKED:str = "timeline_position_clicked"
    TIMELINE_POSITION_STOPPED:str = "timeline_position_stopped"
    PLAYBACK_STATE_CHANGED:str = "playback_state_changed"
    TIMELINE_MODE_CHANGED: str = "timeline_mode_changed"
    SCREENPLAY_SCENE_SELECTED: str = "screenplay_scene_selected"

    # UI Component Signals
    signals = {
        TIMELINE_POSITION_CLICKED:signal(TIMELINE_POSITION_CLICKED),
        TIMELINE_POSITION_STOPPED:signal(TIMELINE_POSITION_STOPPED),
        PLAYBACK_STATE_CHANGED:signal(PLAYBACK_STATE_CHANGED),
        TIMELINE_MODE_CHANGED: signal(TIMELINE_MODE_CHANGED),
        SCREENPLAY_SCENE_SELECTED: signal(SCREENPLAY_SCENE_SELECTED),
    }


    def __new__(cls):
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(Signals, cls).__new__(cls)
        return cls._instance
    
    def connect(self, signal_name:str, func):
        """Connect to timeline position clicked UI signal"""
        self.signals[signal_name].connect(func)

    def send(self, signal_name:str, params: Any):
        """Send timeline position clicked UI signal"""
        self.signals[signal_name].send(self, params=params)
