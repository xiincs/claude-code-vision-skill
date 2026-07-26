import sys
import types
from unittest.mock import MagicMock

import pytest

import vision


# ── resolve_provider ─────────────────────────────────────────────────
def test_resolve_provider_explicit_valid():
    name, config = vision.resolve_provider("qwen")
    assert name == "qwen"
    assert config == vision.PROVIDERS["qwen"]


def test_resolve_provider_explicit_invalid_exits():
    with pytest.raises(SystemExit):
        vision.resolve_provider("bogus")


def test_resolve_provider_env_valid(monkeypatch):
    monkeypatch.setenv("VISION_PROVIDER", "openai")
    name, config = vision.resolve_provider(None)
    assert name == "openai"
    assert config == vision.PROVIDERS["openai"]


def test_resolve_provider_env_invalid_exits(monkeypatch):
    monkeypatch.setenv("VISION_PROVIDER", "bogus")
    with pytest.raises(SystemExit):
        vision.resolve_provider(None)


def test_resolve_provider_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("VISION_PROVIDER", "qwen")
    name, _ = vision.resolve_provider("openai")
    assert name == "openai"


def test_resolve_provider_autodetect_precedence(monkeypatch):
    # doubao/qwen keys unset, openai and anthropic set -> openai wins (dict order)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")
    name, _ = vision.resolve_provider(None)
    assert name == "openai"


def test_resolve_provider_autodetect_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")
    name, _ = vision.resolve_provider(None)
    assert name == "anthropic"


def test_resolve_provider_default_fallback():
    name, config = vision.resolve_provider(None)
    assert name == "doubao"
    assert config == vision.PROVIDERS["doubao"]


# ── resolve_model ────────────────────────────────────────────────────
def test_resolve_model_default_fallback():
    for name, config in vision.PROVIDERS.items():
        assert vision.resolve_model(name, config) == config["model_default"]


def test_resolve_model_provider_specific_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-custom")
    model = vision.resolve_model("anthropic", vision.PROVIDERS["anthropic"])
    assert model == "claude-custom"


def test_resolve_model_global_override(monkeypatch):
    monkeypatch.setenv("VISION_MODEL", "global-model")
    for name, config in vision.PROVIDERS.items():
        assert vision.resolve_model(name, config) == "global-model"


def test_resolve_model_global_overrides_provider_specific(monkeypatch):
    monkeypatch.setenv("VISION_MODEL", "global-model")
    monkeypatch.setenv("ANTHROPIC_MODEL", "provider-model")
    model = vision.resolve_model("anthropic", vision.PROVIDERS["anthropic"])
    assert model == "global-model"


# ── MIME mapping ─────────────────────────────────────────────────────
@pytest.mark.parametrize("ext,expected", [
    (".png", "image/png"),
    (".jpg", "image/jpeg"),
    (".jpeg", "image/jpeg"),
    (".webp", "image/webp"),
    (".gif", "image/gif"),
])
def test_mime_map_known_extensions(ext, expected):
    assert vision.MIME_MAP.get(ext, "image/png") == expected


def test_mime_map_unknown_extension_falls_back_to_png():
    assert vision.MIME_MAP.get(".bmp", "image/png") == "image/png"


# ── request-shape: openai-compatible path ───────────────────────────
def test_vision_openai_compatible_request_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    image_path = tmp_path / "shot.png"
    image_path.write_bytes(b"fake-png-bytes")

    fake_response = MagicMock()
    fake_response.choices[0].message.content = "looks fine"

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response
    monkeypatch.setattr(vision, "OpenAI", MagicMock(return_value=fake_client))

    result = vision.vision_openai_compatible(
        str(image_path), "describe this", "openai", vision.PROVIDERS["openai"]
    )

    assert result == "looks fine"

    _, call_kwargs = fake_client.chat.completions.create.call_args
    assert call_kwargs["model"] == "gpt-4o"

    content_blocks = call_kwargs["messages"][0]["content"]
    assert content_blocks[0]["type"] == "image_url"
    assert content_blocks[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert content_blocks[1] == {"type": "text", "text": "describe this"}


def test_vision_openai_compatible_missing_key_exits(tmp_path):
    image_path = tmp_path / "shot.png"
    image_path.write_bytes(b"fake-png-bytes")

    with pytest.raises(SystemExit):
        vision.vision_openai_compatible(
            str(image_path), "describe this", "openai", vision.PROVIDERS["openai"]
        )


# ── request-shape: anthropic path ───────────────────────────────────
def test_vision_anthropic_request_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    image_path = tmp_path / "shot.png"
    image_path.write_bytes(b"fake-png-bytes")

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="looks fine")]

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    fake_anthropic_module = types.ModuleType("anthropic")
    fake_anthropic_module.Anthropic = MagicMock(return_value=fake_client)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    result = vision.vision_anthropic(
        str(image_path), "describe this", "anthropic", vision.PROVIDERS["anthropic"]
    )

    assert result == "looks fine"

    _, call_kwargs = fake_client.messages.create.call_args
    assert call_kwargs["model"] == "claude-sonnet-5"

    content_blocks = call_kwargs["messages"][0]["content"]
    assert content_blocks[0]["type"] == "image"
    assert content_blocks[0]["source"]["type"] == "base64"
    assert content_blocks[0]["source"]["media_type"] == "image/png"
    assert content_blocks[1] == {"type": "text", "text": "describe this"}


def test_vision_anthropic_missing_key_exits(tmp_path):
    image_path = tmp_path / "shot.png"
    image_path.write_bytes(b"fake-png-bytes")

    with pytest.raises(SystemExit):
        vision.vision_anthropic(
            str(image_path), "describe this", "anthropic", vision.PROVIDERS["anthropic"]
        )


# ── vision() dispatch ────────────────────────────────────────────────
def test_vision_dispatches_to_anthropic(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    image_path = tmp_path / "shot.png"
    image_path.write_bytes(b"fake-png-bytes")

    called = {}

    def fake_vision_anthropic(*args, **kwargs):
        called["yes"] = True
        return "ok"

    monkeypatch.setattr(vision, "vision_anthropic", fake_vision_anthropic)
    result = vision.vision(str(image_path), "p", "anthropic", vision.PROVIDERS["anthropic"])

    assert result == "ok"
    assert called.get("yes") is True


def test_vision_dispatches_to_openai_compatible_for_others(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    image_path = tmp_path / "shot.png"
    image_path.write_bytes(b"fake-png-bytes")

    called = {}

    def fake_vision_openai_compatible(*args, **kwargs):
        called["yes"] = True
        return "ok"

    monkeypatch.setattr(vision, "vision_openai_compatible", fake_vision_openai_compatible)
    result = vision.vision(str(image_path), "p", "openai", vision.PROVIDERS["openai"])

    assert result == "ok"
    assert called.get("yes") is True
