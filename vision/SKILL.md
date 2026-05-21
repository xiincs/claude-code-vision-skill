---
name: vision
description: Call vision models (Doubao, Qwen, OpenAI) to analyze images. Use when you need to understand screenshots, UI layouts, diagrams, or any image content. Supports png/jpg/webp/gif.
---

# vision

Multi-provider vision tool. Call various vision models to describe images. Feed it a prompt + image path, get back a text description.

## Quick start

```bash
python vision.py [--provider <name>] <image_path> <prompt>
```

When `--provider` is omitted, the provider is resolved by: `--provider` flag > `VISION_PROVIDER` env > first API key found.

## Providers

### doubao (豆包 / Volcengine Ark)

- API key: `DOUBAO_API_KEY`
- Default model: `doubao-seed-2-0-pro-260215`
- Custom endpoint: `DOUBAO_BASE_URL`

### qwen (通义千问 / DashScope)

- API key: `DASHSCOPE_API_KEY`
- Default model: `qwen-vl-max`
- Custom endpoint: `DASHSCOPE_BASE_URL`
- Available models: `qwen-vl-max`, `qwen-vl-plus`, `qvq-max`

### openai (GPT-4o)

- API key: `OPENAI_API_KEY`
- Default model: `gpt-4o`
- Custom endpoint: `OPENAI_BASE_URL`
- Also works with any OpenAI-compatible endpoint.

## Configuration

| Env Var | Scope | Default |
|----------|-------|---------|
| `VISION_PROVIDER` | Default provider | auto-detect |
| `VISION_MODEL` | Override model (all providers) | provider default |
| `{PROVIDER}_MODEL` | Override model (per provider) | — |
| `VISION_TEMPERATURE` | Response creativity 0–1 | `0` |
| `VISION_MAX_TOKENS` | Max response tokens | `4096` |

## Examples

```bash
# Auto-detect provider from API keys
python vision.py "screenshot.png" "Describe the page layout and any visible UI issues."

# Explicit provider
python vision.py --provider qwen "mockup.png" "List all components, colors, and spacing patterns."

# Custom model
QWEN_MODEL=qvq-max python vision.py --provider qwen "diagram.png" "Explain the architecture."

# GPT-4o for visual regression
python vision.py -p openai "after.png" "Compare with app design spec, flag differences."
```
