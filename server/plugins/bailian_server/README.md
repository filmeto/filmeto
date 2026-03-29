# Bailian Server Plugin

Alibaba Cloud DashScope (Bailian) integration for Filmeto. Supports LLM chat and AIGC image generation.

## Features

- **LLM Chat**: OpenAI-compatible chat completion via DashScope API
- **Coding Plan**: AI coding assistant with code generation capabilities
- **Text-to-Image**: Generate images using Wanx models
- **Image-to-Image**: Transform images with text prompts
- **Video Generation**: Text-to-video and image-to-video (planned)
- **Speech**: Text-to-speech and speech recognition (planned)
- **Embedding**: Text and multimodal embeddings (planned)

## Quick Start

### 1. Get API Key

1. Go to [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. Navigate to **DashScope** → **API-KEY管理**
3. Create a new API Key

### 2. Configure Server

Only **one field** is required:

| Field | Required | Description |
|-------|----------|-------------|
| API Key | Yes | DashScope API Key |

Optional settings:
- **Default Chat Model**: qwen-max (default), qwen-plus, qwen-turbo, etc.
- **Default Image Model**: wanx2.1-t2i-turbo (default), wanx2.1-t2i-plus

### 3. Coding Plan (Optional)

Coding Plan is an AI coding assistant that requires a separate subscription.

1. Go to [Coding Plan Page](https://bailian.console.aliyun.com/) to subscribe
2. Get the Coding Plan API Key (format: `sk-sp-xxxxx`)
3. Enable Coding Plan in configuration and enter the API Key

| Field | Description |
|-------|-------------|
| Enable Coding Plan | Toggle to enable Coding Plan feature |
| Coding Plan API Key | API Key for Coding Plan (sk-sp-xxxxx format) |

## Supported Models

All models are configured in `models.yml`. See that file for the complete list and to add new models.

### Flagship Models (Qwen3 Series)

| Model | Description |
|-------|-------------|
| qwen3-max | Qwen3 flagship model, most capable |
| qwen3-235b-a22b | Hybrid expert model (235B total, 22B active) |
| qwen3-32b | Qwen3 32B parameter model |

### LLM Models (Chat)

| Model | Description |
|-------|-------------|
| qwen-max | Most capable model for complex tasks |
| qwen-max-latest | Latest version of qwen-max |
| qwen-plus | Balance of speed and quality |
| qwen-plus-latest | Latest version of qwen-plus |
| qwen-flash | Ultra-fast model for simple tasks |
| qwen-turbo | Fast and efficient model |
| qwen-turbo-latest | Latest version of qwen-turbo |
| qwen-long | Long context support (up to 10K tokens) |

### Reasoning Models

| Model | Description |
|-------|-------------|
| qwq-plus | QwQ reasoning model for complex reasoning |
| qwq-32b | QwQ 32B reasoning model |

### Vision-Language Models

| Model | Description |
|-------|-------------|
| qvq-max | Visual reasoning for image understanding |
| qvq-max-latest | Latest version of qvq-max |
| qwen-vl-max | Vision-language model (most capable) |
| qwen-vl-max-latest | Latest version of qwen-vl-max |
| qwen-vl-plus | Vision-language model (balanced) |
| qwen-vl-ocr | OCR-optimized vision model |

### Multimodal Models

| Model | Description |
|-------|-------------|
| qwen-omni | Multimodal model supporting text, image, audio |
| qwen-audio | Audio understanding model |

### Specialized Models

| Model | Description |
|-------|-------------|
| qwen-coder | Code-specialized model |
| qwen-coder-plus | Enhanced code-specialized model |
| qwen-mt | Machine translation model |

### Open Source Models (Qwen2.5)

| Model | Description |
|-------|-------------|
| qwen2.5-72b-instruct | Qwen 2.5 72B open source model |
| qwen2.5-32b-instruct | Qwen 2.5 32B open source model |
| qwen2.5-14b-instruct | Qwen 2.5 14B open source model |
| qwen2.5-7b-instruct | Qwen 2.5 7B open source model |

### Third-Party Models

| Model | Description |
|-------|-------------|
| deepseek-r1 | DeepSeek R1 reasoning model |
| deepseek-v3 | DeepSeek V3 general model |
| kimi-k2.5 | Kimi K2.5 model with image understanding |
| glm-4-plus | GLM-4 Plus model |
| glm-4 | GLM-4 general model |
| MiniMax-Text-01 | MiniMax Text-01 model |

### Coding Plan Models

These models require Coding Plan subscription. In the UI, they are prefixed with `code_plan:` to distinguish them. When selected, the API calls will use Coding Plan endpoint and API key.

| Model | UI Display Name | Description |
|-------|-----------------|-------------|
| qwen3.5-plus | code_plan:qwen3.5-plus | Supports image understanding |
| kimi-k2.5 | code_plan:kimi-k2.5 | Supports image understanding |
| glm-5 | code_plan:glm-5 | General language model |
| MiniMax-M2.5 | code_plan:MiniMax-M2.5 | General language model |

### Image Models (Wanx)

#### Text-to-Image

| Model | Description |
|-------|-------------|
| wanx2.6-t2i-turbo | Wanx 2.6 fast text-to-image |
| wanx2.6-t2i-plus | Wanx 2.6 high quality text-to-image |
| wanx2.5-t2i-turbo | Wanx 2.5 fast text-to-image |
| wanx2.5-t2i-plus | Wanx 2.5 high quality text-to-image |
| wanx2.2-t2i-turbo | Wanx 2.2 fast text-to-image |
| wanx2.2-t2i-plus | Wanx 2.2 high quality text-to-image |
| wanx2.1-t2i-turbo | Wanx 2.1 fast text-to-image (default) |
| wanx2.1-t2i-plus | Wanx 2.1 high quality text-to-image |

#### Image-to-Image

| Model | Description |
|-------|-------------|
| wanx2.1-i2i-turbo | Fast image-to-image transformation |
| wanx2.1-i2i-plus | High quality image-to-image transformation |

#### Image Editing

| Model | Description |
|-------|-------------|
| wanx2.1-imgedit-turbo | Fast image editing |
| wanx2.1-imgedit-plus | High quality image editing |

### Video Models (Wanx)

| Model | Description |
|-------|-------------|
| wanx2.1-t2v-turbo | Fast text-to-video generation |
| wanx2.1-t2v-plus | High quality text-to-video generation |
| wanx2.1-i2v-turbo | Fast image-to-video generation |
| wanx2.1-i2v-plus | High quality image-to-video generation |

### Speech Models

#### Text-to-Speech (TTS)

| Model | Description |
|-------|-------------|
| qwen-tts | Qwen text-to-speech model |
| cosyvoice-v1 | CosyVoice TTS model |
| sambert | Sambert TTS model |

#### Automatic Speech Recognition (ASR)

| Model | Description |
|-------|-------------|
| qwen-asr | Qwen automatic speech recognition |
| paraformer-v2 | Paraformer ASR model |

### Embedding Models

#### Text Embedding

| Model | Description |
|-------|-------------|
| text-embedding-v3 | Latest text embedding model |
| text-embedding-v2 | Text embedding model v2 |

#### Multimodal Embedding

| Model | Description |
|-------|-------------|
| multimodal-embedding-v1 | Multimodal embedding for text and images |

## Requirements

- Python >= 3.9
- dashscope (for chat completion and image generation with SDK)

## Installation

```bash
pip install dashscope pillow
```

## Configuration Schema

```yaml
# Minimal configuration - only API Key needed
api_key: "sk-xxxxxxxx"  # Required

# Coding Plan (optional)
coding_plan_enabled: false
coding_plan_api_key: "sk-sp-xxxxx"

# Optional
default_model: "qwen-max"
default_image_model: "wanx2.1-t2i-turbo"
```

## API Endpoints

| Service | Endpoint |
|---------|----------|
| DashScope Chat | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| DashScope Image | https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis |
| DashScope Video | https://dashscope.aliyuncs.com/api/v1/services/aigc/text2video/video-synthesis |
| DashScope Speech | https://dashscope.aliyuncs.com/api/v1/services/audio |
| DashScope Embedding | https://dashscope.aliyuncs.com/api/v1/services/embeddings |
| Coding Plan | https://coding.dashscope.aliyuncs.com/v1 |

## Documentation

- [DashScope API Documentation](https://help.aliyun.com/zh/model-studio/)
- [API Key Management](https://help.aliyun.com/zh/model-studio/developer-reference/api-key-management)
- [Model Documentation](https://help.aliyun.com/zh/model-studio/getting-started/models)
- [Coding Plan Documentation](https://help.aliyun.com/zh/model-studio/developer-reference/coding-plan)