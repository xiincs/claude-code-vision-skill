"""
Multi-provider vision tool.
Usage: python vision.py [--provider <name>] <image_path> <prompt>

Providers: doubao (豆包), qwen (通义千问), openai
Set one of: DOUBAO_API_KEY, DASHSCOPE_API_KEY, OPENAI_API_KEY
"""
import sys
import os
import base64
import argparse
from pathlib import Path
from openai import OpenAI

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── provider registry ──────────────────────────────────────────────
PROVIDERS = {
    "doubao": {
        "key_env": "DOUBAO_API_KEY",
        "base_env": "DOUBAO_BASE_URL",
        "base_default": "https://ark.cn-beijing.volces.com/api/v3",
        "model_default": "doubao-seed-2-0-pro-260215",
    },
    "qwen": {
        "key_env": "DASHSCOPE_API_KEY",
        "base_env": "DASHSCOPE_BASE_URL",
        "base_default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_default": "qwen-vl-max",
    },
    "openai": {
        "key_env": "OPENAI_API_KEY",
        "base_env": "OPENAI_BASE_URL",
        "base_default": "https://api.openai.com/v1",
        "model_default": "gpt-4o",
    },
}

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


# ── helpers ─────────────────────────────────────────────────────────
def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def resolve_provider(name: str | None) -> tuple[str, dict]:
    # explicit --provider flag
    if name:
        if name not in PROVIDERS:
            names = ", ".join(PROVIDERS)
            print(f"Error: unknown provider '{name}'. Available: {names}", file=sys.stderr)
            sys.exit(1)
        return name, PROVIDERS[name]

    # VISION_PROVIDER env var
    env_provider = os.environ.get("VISION_PROVIDER", "").lower()
    if env_provider:
        if env_provider not in PROVIDERS:
            names = ", ".join(PROVIDERS)
            print(f"Error: VISION_PROVIDER='{env_provider}' is invalid. Available: {names}", file=sys.stderr)
            sys.exit(1)
        return env_provider, PROVIDERS[env_provider]

    # auto-detect: first provider whose API key is set
    for pname, pconf in PROVIDERS.items():
        if os.environ.get(pconf["key_env"]):
            return pname, pconf

    return "doubao", PROVIDERS["doubao"]


def resolve_model(provider_name: str, config: dict) -> str:
    # VISION_MODEL (global override, highest priority)
    global_model = os.environ.get("VISION_MODEL", "")
    if global_model:
        return global_model

    # provider-specific env: {PROVIDER}_MODEL
    provider_model_env = f"{provider_name.upper()}_MODEL"
    provider_model = os.environ.get(provider_model_env, "")
    if provider_model:
        return provider_model

    return config["model_default"]


# ── main ────────────────────────────────────────────────────────────
def vision(image_path: str, prompt: str, provider_name: str, config: dict) -> str:
    api_key = os.environ.get(config["key_env"], "")
    if not api_key:
        print(f"Error: {config['key_env']} env var is not set", file=sys.stderr)
        sys.exit(1)

    model = resolve_model(provider_name, config)
    base_url = os.environ.get(config["base_env"], config["base_default"])
    temperature = float(os.environ.get("VISION_TEMPERATURE", "0"))
    max_tokens = int(os.environ.get("VISION_MAX_TOKENS", "4096"))

    ext = Path(image_path).suffix.lower()
    mime = MIME_MAP.get(ext, "image/png")
    b64 = encode_image(image_path)
    data_uri = f"data:{mime};base64,{b64}"

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


# ── cli ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Multi-provider vision tool")
    parser.add_argument("--provider", "-p", choices=list(PROVIDERS), default=None,
                        help="Vision model provider (auto-detected from env if omitted)")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("prompt", help="Text prompt for the vision model")
    args = parser.parse_args()

    if not os.path.exists(args.image_path):
        print(f"Error: file not found: {args.image_path}", file=sys.stderr)
        sys.exit(1)

    provider_name, config = resolve_provider(args.provider)

    try:
        result = vision(args.image_path, args.prompt, provider_name, config)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
