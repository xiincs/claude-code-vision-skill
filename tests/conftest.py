import sys
from pathlib import Path

import pytest

VISION_DIR = Path(__file__).resolve().parent.parent / "vision"
if str(VISION_DIR) not in sys.path:
    sys.path.insert(0, str(VISION_DIR))

ENV_VARS_TO_CLEAR = [
    "DOUBAO_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "DOUBAO_BASE_URL", "DASHSCOPE_BASE_URL", "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL",
    "VISION_PROVIDER", "VISION_MODEL", "VISION_TEMPERATURE", "VISION_MAX_TOKENS",
    "DOUBAO_MODEL", "QWEN_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL",
]


@pytest.fixture(autouse=True)
def clean_vision_env(monkeypatch):
    """Isolate every test from whatever vision-related env vars the host shell has set."""
    for var in ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)
