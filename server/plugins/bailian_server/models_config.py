"""
Bailian Models Configuration Loader

Loads model definitions from models.yml and provides utilities for model management.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


# Coding Plan model prefix for UI display
CODING_PLAN_PREFIX = "code_plan:"


class ModelsConfig:
    """Manages Bailian model configuration loaded from models.yml."""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from models.yml."""
        config_path = Path(__file__).parent / "models.yml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
        else:
            # Fallback to defaults if file not found
            self._config = self._get_defaults()

    def _get_defaults(self) -> Dict[str, Any]:
        """Return default configuration if models.yml is not available."""
        return {
            "dashscope_models": [
                {"name": "qwen3-max", "description": "Qwen3 flagship model", "supports_vision": False},
                {"name": "qwen-max", "description": "Most capable model", "supports_vision": False},
                {"name": "qwen-plus", "description": "Balanced model", "supports_vision": False},
                {"name": "qwen-flash", "description": "Ultra-fast model", "supports_vision": False},
                {"name": "qwen-turbo", "description": "Fast model", "supports_vision": False},
                {"name": "qwen-long", "description": "Long context", "supports_vision": False},
                {"name": "qwq-plus", "description": "Reasoning model", "supports_vision": False},
                {"name": "qvq-max", "description": "Visual reasoning", "supports_vision": True},
                {"name": "qwen-vl-max", "description": "Vision model", "supports_vision": True},
                {"name": "qwen-vl-plus", "description": "Vision model", "supports_vision": True},
                {"name": "qwen-vl-ocr", "description": "OCR model", "supports_vision": True},
                {"name": "qwen-omni", "description": "Multimodal model", "supports_vision": True, "supports_audio": True},
                {"name": "qwen-audio", "description": "Audio model", "supports_vision": False, "supports_audio": True},
                {"name": "qwen-coder", "description": "Code model", "supports_vision": False},
                {"name": "qwen-mt", "description": "Translation model", "supports_vision": False},
                {"name": "qwen2.5-72b-instruct", "description": "Qwen 2.5 72B", "supports_vision": False},
                {"name": "qwen2.5-32b-instruct", "description": "Qwen 2.5 32B", "supports_vision": False},
            ],
            "third_party_models": [
                {"name": "deepseek-r1", "description": "DeepSeek R1", "supports_vision": False},
                {"name": "deepseek-v3", "description": "DeepSeek V3", "supports_vision": False},
                {"name": "kimi-k2.5", "description": "Kimi K2.5", "supports_vision": True},
                {"name": "glm-4-plus", "description": "GLM-4 Plus", "supports_vision": False},
                {"name": "MiniMax-Text-01", "description": "MiniMax Text", "supports_vision": False},
            ],
            "coding_plan_models": [
                {"name": "qwen3.5-plus", "description": "Coding model with vision", "supports_vision": True},
                {"name": "kimi-k2.5", "description": "Kimi with vision", "supports_vision": True},
                {"name": "glm-5", "description": "GLM-5", "supports_vision": False},
                {"name": "MiniMax-M2.5", "description": "MiniMax", "supports_vision": False},
            ],
            "image_models": {
                "text_to_image": [
                    {"name": "wanx2.6-t2i-turbo", "description": "Wanx 2.6 Fast T2I", "default": False},
                    {"name": "wanx2.6-t2i-plus", "description": "Wanx 2.6 Quality T2I", "default": False},
                    {"name": "wanx2.1-t2i-turbo", "description": "Wanx 2.1 Fast T2I", "default": True},
                    {"name": "wanx2.1-t2i-plus", "description": "Wanx 2.1 Quality T2I", "default": False},
                ],
                "image_to_image": [
                    {"name": "wanx2.1-i2i-turbo", "description": "Fast I2I", "default": True},
                ],
                "image_editing": [
                    {"name": "wanx2.1-imgedit-turbo", "description": "Fast image editing", "default": True},
                ],
            },
            "video_models": {
                "text_to_video": [
                    {"name": "wanx2.1-t2v-turbo", "description": "Fast T2V", "default": True},
                ],
                "image_to_video": [
                    {"name": "wanx2.1-i2v-turbo", "description": "Fast I2V", "default": True},
                ],
                "speech_to_video": [
                    {"name": "wan2.2-s2v", "description": "Wan audio-driven lip-sync", "default": True},
                ],
            },
            "music_models": {
                "text_to_music": [
                    {"name": "cosyvoice-v3-flash", "description": "CosyVoice styled vocal", "default": True},
                ],
            },
            "speech_models": {
                "tts": [
                    {"name": "qwen3-tts-flash", "description": "Qwen3 TTS flash", "default": True},
                    {"name": "qwen-tts", "description": "Legacy name maps to Qwen3 TTS", "default": False},
                ],
                "asr": [
                    {"name": "qwen-asr", "description": "Qwen ASR", "default": True},
                ],
            },
            "embedding_models": {
                "text": [
                    {"name": "text-embedding-v3", "description": "Text embedding v3", "default": True},
                ],
                "multimodal": [
                    {"name": "multimodal-embedding-v1", "description": "Multimodal embedding", "default": True},
                ],
            },
            "endpoints": {
                "dashscope_chat": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "dashscope_image": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                "dashscope_video": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2video/video-synthesis",
                "dashscope_speech": "https://dashscope.aliyuncs.com/api/v1/services/audio",
                "dashscope_embedding": "https://dashscope.aliyuncs.com/api/v1/services/embeddings",
                "coding_plan": "https://coding.dashscope.aliyuncs.com/v1",
            },
        }

    def reload(self):
        """Reload configuration from file."""
        self._load_config()

    # ============================================================
    # DashScope Models
    # ============================================================

    def get_dashscope_models(self) -> List[str]:
        """Get list of DashScope model names."""
        models = self._config.get("dashscope_models", [])
        return [m["name"] for m in models]

    def get_dashscope_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a DashScope model."""
        models = self._config.get("dashscope_models", [])
        for m in models:
            if m["name"] == model_name:
                return m
        return None

    # ============================================================
    # Coding Plan Models
    # ============================================================

    def get_coding_plan_models(self, with_prefix: bool = False) -> List[str]:
        """
        Get list of Coding Plan model names.

        Args:
            with_prefix: If True, return names with 'code_plan:' prefix for UI display
        """
        models = self._config.get("coding_plan_models", [])
        names = [m["name"] for m in models]
        if with_prefix:
            names = [f"{CODING_PLAN_PREFIX}{name}" for name in names]
        return names

    def get_coding_plan_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a Coding Plan model (strip prefix if present)."""
        # Strip prefix if present
        if model_name.startswith(CODING_PLAN_PREFIX):
            model_name = model_name[len(CODING_PLAN_PREFIX):]

        models = self._config.get("coding_plan_models", [])
        for m in models:
            if m["name"] == model_name:
                return m
        return None

    def is_coding_plan_model(self, model_name: str) -> bool:
        """Check if a model name (with or without prefix) is a Coding Plan model."""
        # Strip prefix if present
        if model_name.startswith(CODING_PLAN_PREFIX):
            model_name = model_name[len(CODING_PLAN_PREFIX):]

        models = self.get_coding_plan_models(with_prefix=False)
        return model_name in models

    def strip_coding_plan_prefix(self, model_name: str) -> str:
        """Remove the Coding Plan prefix from a model name if present."""
        if model_name.startswith(CODING_PLAN_PREFIX):
            return model_name[len(CODING_PLAN_PREFIX):]
        return model_name

    def add_coding_plan_prefix(self, model_name: str) -> str:
        """Add the Coding Plan prefix to a model name."""
        if not model_name.startswith(CODING_PLAN_PREFIX):
            return f"{CODING_PLAN_PREFIX}{model_name}"
        return model_name

    # ============================================================
    # Image Models
    # ============================================================

    def get_text_to_image_models(self) -> List[str]:
        """Get list of text-to-image model names."""
        models = self._config.get("image_models", {}).get("text_to_image", [])
        return [m["name"] for m in models]

    def get_default_text_to_image_model(self) -> str:
        """Get the default text-to-image model name."""
        models = self._config.get("image_models", {}).get("text_to_image", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "wanx2.1-t2i-turbo"

    def get_image_to_image_models(self) -> List[str]:
        """Get list of image-to-image model names."""
        models = self._config.get("image_models", {}).get("image_to_image", [])
        return [m["name"] for m in models]

    def get_default_image_to_image_model(self) -> str:
        """Get the default image-to-image model name."""
        models = self._config.get("image_models", {}).get("image_to_image", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "wanx2.1-i2i-turbo"

    # ============================================================
    # Endpoints
    # ============================================================

    def get_dashscope_chat_endpoint(self) -> str:
        """Get DashScope chat endpoint."""
        return self._config.get("endpoints", {}).get(
            "dashscope_chat",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def get_dashscope_image_endpoint(self) -> str:
        """Get DashScope image endpoint."""
        return self._config.get("endpoints", {}).get(
            "dashscope_image",
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        )

    def get_coding_plan_endpoint(self) -> str:
        """Get Coding Plan endpoint."""
        return self._config.get("endpoints", {}).get(
            "coding_plan",
            "https://coding.dashscope.aliyuncs.com/v1"
        )

    def get_dashscope_video_endpoint(self) -> str:
        """Get DashScope video endpoint."""
        return self._config.get("endpoints", {}).get(
            "dashscope_video",
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2video/video-synthesis"
        )

    def get_dashscope_speech_endpoint(self) -> str:
        """Get DashScope speech endpoint."""
        return self._config.get("endpoints", {}).get(
            "dashscope_speech",
            "https://dashscope.aliyuncs.com/api/v1/services/audio"
        )

    def get_dashscope_embedding_endpoint(self) -> str:
        """Get DashScope embedding endpoint."""
        return self._config.get("endpoints", {}).get(
            "dashscope_embedding",
            "https://dashscope.aliyuncs.com/api/v1/services/embeddings"
        )

    # ============================================================
    # Third-Party Models
    # ============================================================

    def get_third_party_models(self) -> List[str]:
        """Get list of third-party model names."""
        models = self._config.get("third_party_models", [])
        return [m["name"] for m in models]

    def get_third_party_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a third-party model."""
        models = self._config.get("third_party_models", [])
        for m in models:
            if m["name"] == model_name:
                return m
        return None

    # ============================================================
    # Video Models
    # ============================================================

    def get_text_to_video_models(self) -> List[str]:
        """Get list of text-to-video model names."""
        models = self._config.get("video_models", {}).get("text_to_video", [])
        return [m["name"] for m in models]

    def get_default_text_to_video_model(self) -> str:
        """Get the default text-to-video model name."""
        models = self._config.get("video_models", {}).get("text_to_video", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "wanx2.1-t2v-turbo"

    def get_image_to_video_models(self) -> List[str]:
        """Get list of image-to-video model names."""
        models = self._config.get("video_models", {}).get("image_to_video", [])
        return [m["name"] for m in models]

    def get_default_image_to_video_model(self) -> str:
        """Get the default image-to-video model name."""
        models = self._config.get("video_models", {}).get("image_to_video", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "wanx2.1-i2v-turbo"

    def get_speech_to_video_models(self) -> List[str]:
        """Models for speech/audio-driven lip-sync video (e.g. wan2.2-s2v)."""
        models = self._config.get("video_models", {}).get("speech_to_video", [])
        return [m["name"] for m in models]

    def get_default_speech_to_video_model(self) -> str:
        models = self._config.get("video_models", {}).get("speech_to_video", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "wan2.2-s2v"

    # ============================================================
    # Speech Models
    # ============================================================

    def get_tts_models(self) -> List[str]:
        """Get list of text-to-speech model names."""
        models = self._config.get("speech_models", {}).get("tts", [])
        return [m["name"] for m in models]

    def get_default_tts_model(self) -> str:
        """Get the default TTS model name."""
        models = self._config.get("speech_models", {}).get("tts", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "qwen-tts"

    def get_asr_models(self) -> List[str]:
        """Get list of automatic speech recognition model names."""
        models = self._config.get("speech_models", {}).get("asr", [])
        return [m["name"] for m in models]

    def get_default_asr_model(self) -> str:
        """Get the default ASR model name."""
        models = self._config.get("speech_models", {}).get("asr", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "qwen-asr"

    # ============================================================
    # Music (styled vocal / prompt-to-audio via CosyVoice)
    # ============================================================

    def get_text_to_music_models(self) -> List[str]:
        models = self._config.get("music_models", {}).get("text_to_music", [])
        return [m["name"] for m in models]

    def get_default_text_to_music_model(self) -> str:
        models = self._config.get("music_models", {}).get("text_to_music", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "cosyvoice-v3-flash"

    # ============================================================
    # Embedding Models
    # ============================================================

    def get_text_embedding_models(self) -> List[str]:
        """Get list of text embedding model names."""
        models = self._config.get("embedding_models", {}).get("text", [])
        return [m["name"] for m in models]

    def get_default_text_embedding_model(self) -> str:
        """Get the default text embedding model name."""
        models = self._config.get("embedding_models", {}).get("text", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "text-embedding-v3"

    def get_multimodal_embedding_models(self) -> List[str]:
        """Get list of multimodal embedding model names."""
        models = self._config.get("embedding_models", {}).get("multimodal", [])
        return [m["name"] for m in models]

    def get_default_multimodal_embedding_model(self) -> str:
        """Get the default multimodal embedding model name."""
        models = self._config.get("embedding_models", {}).get("multimodal", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "multimodal-embedding-v1"

    # ============================================================
    # Image Editing Models
    # ============================================================

    def get_image_editing_models(self) -> List[str]:
        """Get list of image editing model names."""
        models = self._config.get("image_models", {}).get("image_editing", [])
        return [m["name"] for m in models]

    def get_default_image_editing_model(self) -> str:
        """Get the default image editing model name."""
        models = self._config.get("image_models", {}).get("image_editing", [])
        for m in models:
            if m.get("default"):
                return m["name"]
        return models[0]["name"] if models else "wanx2.1-imgedit-turbo"

    # ============================================================
    # All Chat Models (for UI)
    # ============================================================

    def get_all_chat_models(self, coding_plan_enabled: bool = False, include_third_party: bool = True) -> List[str]:
        """
        Get all chat model names for UI display.

        Args:
            coding_plan_enabled: If True, include Coding Plan models with prefix
            include_third_party: If True, include third-party models
        """
        models = self.get_dashscope_models()
        if include_third_party:
            models.extend(self.get_third_party_models())
        if coding_plan_enabled:
            coding_plan_models = self.get_coding_plan_models(with_prefix=True)
            models.extend(coding_plan_models)
        return models


# Global instance
models_config = ModelsConfig()