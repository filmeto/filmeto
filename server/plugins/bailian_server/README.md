# Bailian Server Plugin

Alibaba Cloud DashScope (Bailian) integration for Filmeto. Supports LLM chat and AIGC image generation.

## Features

- **LLM Chat**: OpenAI-compatible chat completion via DashScope API
- **Coding Plan**: AI coding assistant with code generation capabilities
- **Text-to-Image**: Generate images using Wanx models
- **Image-to-Image**: Transform images with text prompts

## Quick Start

### 1. Get API Key

1. Go to [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. Navigate to **DashScope** → **API-KEY管理**
3. Create a new API Key

### 2. Configure Server

Only **one field** is required:

| Field | Required | Description |
|-------|----------|-------------|
| API Key | ✅ Yes | DashScope API Key |

Optional settings:
- **Default Chat Model**: qwen-max (default), qwen-plus, qwen-turbo, qwen2.5-72b-instruct
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

### LLM Models (Chat)

| Model | Description |
|-------|-------------|
| qwen-max | Most capable model |
| qwen-plus | Balance of speed and quality |
| qwen-turbo | Fast and efficient |
| qwen2.5-72b-instruct | Latest generation |
| qwen-long | Long context support |
| qwen-vl-max | Vision-language model |

### Coding Plan Models

These models require Coding Plan subscription. In the UI, they are prefixed with `code_plan:` to distinguish them. When selected, the API calls will use Coding Plan endpoint and API key.

| Model | UI Display Name | Description |
|-------|-----------------|-------------|
| qwen3.5-plus | code_plan:qwen3.5-plus | Supports image understanding |
| kimi-k2.5 | code_plan:kimi-k2.5 | Supports image understanding |
| glm-5 | code_plan:glm-5 | General language model |
| MiniMax-M2.5 | code_plan:MiniMax-M2.5 | General language model |

### Image Models

| Model | Description |
|-------|-------------|
| wanx2.1-t2i-turbo | Fast text-to-image |
| wanx2.1-t2i-plus | High quality generation |
| wanx2.1-i2i-turbo | Image-to-image transformation |

## Requirements

- Python >= 3.9
- litellm >= 1.0.0 (for chat completion)
- dashscope (optional, for image generation with SDK)

## Installation

```bash
pip install litellm pillow
# Optional: for SDK-based image generation
pip install dashscope
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

## Documentation

- [DashScope API Documentation](https://help.aliyun.com/zh/model-studio/)
- [API Key Management](https://help.aliyun.com/zh/model-studio/developer-reference/api-key-management)
- [Model Documentation](https://help.aliyun.com/zh/model-studio/getting-started/models)
- [Coding Plan Documentation](https://help.aliyun.com/zh/model-studio/developer-reference/coding-plan)