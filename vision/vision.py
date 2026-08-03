"""
Multi-provider vision tool.
Usage: python vision.py [--provider <name>] <image_path> <prompt>

Providers: doubao (Volcengine Ark), qwen (DashScope), openai, anthropic (Claude)
Set one of: DOUBAO_API_KEY, DASHSCOPE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
"""
import sys
import os
import re
import json
import base64
import argparse
from pathlib import Path
from urllib.parse import urlparse
from openai import OpenAI

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── provider registry ──────────────────────────────────────────────
# "protocol" picks the request shape: "openai" (chat completions + image_url)
# or "anthropic" (messages API + base64 image block). Covers the two shapes
# implemented below; virtually every OpenAI-compatible endpoint (vLLM, Ollama,
# LiteLLM, OpenRouter, Azure OpenAI, self-hosted proxies, ...) uses "openai".
PROTOCOLS = ("openai", "anthropic")

PROVIDERS = {
    "doubao": {
        "key_env": "DOUBAO_API_KEY",
        "base_env": "DOUBAO_BASE_URL",
        "base_default": "https://ark.cn-beijing.volces.com/api/v3",
        "model_default": "doubao-seed-2-0-pro-260215",
        "protocol": "openai",
    },
    "qwen": {
        "key_env": "DASHSCOPE_API_KEY",
        "base_env": "DASHSCOPE_BASE_URL",
        "base_default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_default": "qwen-vl-max",
        "protocol": "openai",
    },
    "openai": {
        "key_env": "OPENAI_API_KEY",
        "base_env": "OPENAI_BASE_URL",
        "base_default": "https://api.openai.com/v1",
        "model_default": "gpt-4o",
        "protocol": "openai",
    },
    "anthropic": {
        "key_env": "ANTHROPIC_API_KEY",
        "base_env": "ANTHROPIC_BASE_URL",
        "base_default": "https://api.anthropic.com",
        "model_default": "claude-sonnet-5",
        "protocol": "anthropic",
    },
}

# ── routing ─────────────────────────────────────────────────────────
# Text-only models known to be routed here via a relay/proxy (e.g. CC Switch).
# One-directional: a match here can only force "external" (safe — still runs
# the mandatory vision workflow). It must never be used to infer "native" —
# an unrecognized model name always falls through to the checks below,
# never silently skipped.
# Patterns are regexes matched against the lowercased model name with
# re.search — not plain substrings — because three families need a boundary
# plain substrings can't express:
#   - kimi-k2-  Moonshot's text-only Kimi IDs are all "kimi-k2-<suffix>"
#     (kimi-k2-turbo-preview, kimi-k2-thinking, ...). The newer kimi-k2.5/
#     k2.6/k2.7 add vision and use a dot instead of a hyphen after "k2", so
#     anchoring on the hyphen excludes them without listing every ID.
#   - glm-4\.[56](?!v)  Zhipu glues "v" directly onto the version number for
#     GLM-4.x's vision variants (glm-4.6 -> glm-4.6v, glm-4.5 -> glm-4.5v), so
#     a plain prefix match would also catch its own vision variant.
#   - glm-5(?!v)  GLM-5.x's vision counterpart is "glm-5v-turbo" — a flat
#     name, not a version-number suffix, but it still starts with "glm-5" so
#     a plain prefix match would catch it too. Both lookaheads exclude just
#     the "v" that marks the vision line.
TEXT_ONLY_MODEL_PATTERNS = (
    r"deepseek",
    r"qwen3-coder",
    r"glm-4\.[56](?!v)",
    r"glm-5(?!v)",
    r"kimi-k2-",
    r"devstral",
)

# Anthropic's official API never serves a text-only model, so an unmodified
# ANTHROPIC_BASE_URL is a structural guarantee of native vision — not a
# guess the way matching a model name string would be. A relay/proxy that
# swaps the backend (e.g. CC Switch pointing at DeepSeek) has to override
# this URL to redirect traffic, so its presence (pointing elsewhere) is what
# actually makes the backend unverifiable.
OFFICIAL_ANTHROPIC_HOSTS = ("api.anthropic.com",)


def resolve_routing() -> str:
    """Returns "native" or "external".

    Priority: text-only blocklist (always wins) > explicit human-set
    VISION_ROUTING (either value) > no relay override present (structural
    "native") > unverifiable relay with no explicit signal ("external",
    safe default — never silently skipped).
    """
    model_hint = os.environ.get("ANTHROPIC_MODEL", "").lower()
    if any(re.search(p, model_hint) for p in TEXT_ONLY_MODEL_PATTERNS):
        return "external"

    explicit = os.environ.get("VISION_ROUTING", "").lower()
    if explicit:
        return explicit

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    if not base_url or urlparse(base_url).hostname in OFFICIAL_ANTHROPIC_HOSTS:
        return "native"

    return "external"


REQUEST_TIMEOUT = 60

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


def synthesize_provider(name: str) -> dict:
    """Build a provider config for a name outside the built-in registry.

    Reads {NAME}_API_KEY / {NAME}_BASE_URL / {NAME}_MODEL / {NAME}_PROTOCOL,
    the same env-var-naming convention resolve_model() already uses for
    per-provider model overrides. Lets users wire up any OpenAI- or
    Anthropic-shaped endpoint without touching this file.
    """
    prefix = name.upper()
    base_url = os.environ.get(f"{prefix}_BASE_URL", "")
    model = os.environ.get("VISION_MODEL", "") or os.environ.get(f"{prefix}_MODEL", "")

    missing = []
    if not base_url:
        missing.append(f"{prefix}_BASE_URL")
    if not model:
        missing.append(f"{prefix}_MODEL")
    if missing:
        names = ", ".join(PROVIDERS)
        print(
            f"Error: unknown provider '{name}'. Built-in providers: {names}.\n"
            f"To define a custom provider, set: {', '.join(missing)} "
            f"(also {prefix}_API_KEY; optionally {prefix}_PROTOCOL={'|'.join(PROTOCOLS)}, default openai).",
            file=sys.stderr,
        )
        sys.exit(1)

    protocol = os.environ.get(f"{prefix}_PROTOCOL", "openai").lower()
    if protocol not in PROTOCOLS:
        print(f"Error: {prefix}_PROTOCOL must be one of {', '.join(PROTOCOLS)}, got '{protocol}'", file=sys.stderr)
        sys.exit(1)

    return {
        "key_env": f"{prefix}_API_KEY",
        "base_env": f"{prefix}_BASE_URL",
        "base_default": base_url,
        "model_default": model,
        "protocol": protocol,
    }


def resolve_provider(name: str | None) -> tuple[str, dict]:
    # explicit --provider flag
    if name:
        name = name.lower()
        if name in PROVIDERS:
            return name, PROVIDERS[name]
        return name, synthesize_provider(name)

    # VISION_PROVIDER env var
    env_provider = os.environ.get("VISION_PROVIDER", "").lower()
    if env_provider:
        if env_provider in PROVIDERS:
            return env_provider, PROVIDERS[env_provider]
        return env_provider, synthesize_provider(env_provider)

    # auto-detect: first built-in provider whose API key is set
    # (custom providers must be named explicitly — there's no prefix to guess)
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
def vision_openai_compatible(image_path: str, prompt: str, provider_name: str, config: dict) -> str:
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

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=REQUEST_TIMEOUT)
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


def vision_anthropic(image_path: str, prompt: str, provider_name: str, config: dict) -> str:
    api_key = os.environ.get(config["key_env"], "")
    if not api_key:
        print(f"Error: {config['key_env']} env var is not set", file=sys.stderr)
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("Error: the 'anthropic' package is required for --provider anthropic. "
              "Install it with: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    model = resolve_model(provider_name, config)
    base_url = os.environ.get(config["base_env"], config["base_default"])
    temperature = float(os.environ.get("VISION_TEMPERATURE", "0"))
    max_tokens = int(os.environ.get("VISION_MAX_TOKENS", "4096"))

    ext = Path(image_path).suffix.lower()
    mime = MIME_MAP.get(ext, "image/png")
    b64 = encode_image(image_path)

    client = anthropic.Anthropic(api_key=api_key, base_url=base_url, timeout=REQUEST_TIMEOUT)
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime, "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return resp.content[0].text if resp.content else ""


def vision(image_path: str, prompt: str, provider_name: str, config: dict) -> str:
    if config.get("protocol") == "anthropic":
        return vision_anthropic(image_path, prompt, provider_name, config)
    return vision_openai_compatible(image_path, prompt, provider_name, config)


def routing_message(routing: str) -> str:
    if routing == "native":
        return ("VISION_ROUTING=native — native image understanding is expected this "
                 "session; skip this tool and analyze the image directly.")
    return ("VISION_ROUTING=external — no native image understanding this session; "
             "the mandatory vision workflow applies.")


# ── cli ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Multi-provider vision tool")
    builtin = ", ".join(PROVIDERS)
    parser.add_argument("--provider", "-p", default=None,
                        help=f"Vision model provider: built-in ({builtin}), or any custom name backed by "
                             f"{{NAME}}_API_KEY/{{NAME}}_BASE_URL/{{NAME}}_MODEL env vars "
                             f"(auto-detected from env if omitted)")
    parser.add_argument("--check-routing", action="store_true",
                        help="Print 'native' or 'external' and exit — used by SKILL.md to decide "
                             "whether this tool is needed this session")
    parser.add_argument("--session-start-hook", action="store_true",
                        help="Emit a Claude Code SessionStart hook JSON payload and exit")
    parser.add_argument("image_path", nargs="?", help="Path to the image file")
    parser.add_argument("prompt", nargs="?", help="Text prompt for the vision model")
    args = parser.parse_args()

    if args.check_routing:
        print(resolve_routing())
        return

    if args.session_start_hook:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": routing_message(resolve_routing()),
            }
        }))
        return

    if resolve_routing() == "native":
        print(routing_message("native"))
        return

    if not args.image_path or not args.prompt:
        print("Error: image_path and prompt are required", file=sys.stderr)
        sys.exit(1)

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
