import json
import sys
import types
from unittest.mock import MagicMock

import pytest

import vision


# ── resolve_routing ────────────────────────────────────────────────
def test_resolve_routing_default_native_when_no_relay():
    """No ANTHROPIC_BASE_URL override means Claude Code is talking to
    Anthropic's official API directly — every model served there is
    multimodal, so this is a structural fact, not a guess."""
    assert vision.resolve_routing() == "native"


def test_resolve_routing_native_when_base_url_is_official(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    assert vision.resolve_routing() == "native"


def test_resolve_routing_native_when_official_base_url_has_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
    assert vision.resolve_routing() == "native"


def test_resolve_routing_external_when_relay_base_url_present(monkeypatch):
    """A base URL pointing somewhere other than Anthropic's official API is
    exactly the unverifiable-backend case (e.g. CC Switch -> DeepSeek) —
    must stay 'external' with no explicit VISION_ROUTING set."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://my-relay.example.com/v1")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_hostname_check_is_not_a_substring_match(monkeypatch):
    """A relay hostname that merely contains the official domain as a
    substring must not be treated as official — only an exact hostname
    match counts."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com.evil.example/v1")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_explicit_native(monkeypatch):
    monkeypatch.setenv("VISION_ROUTING", "native")
    assert vision.resolve_routing() == "native"


def test_resolve_routing_explicit_external(monkeypatch):
    monkeypatch.setenv("VISION_ROUTING", "external")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_explicit_external_overrides_official_base_url(monkeypatch):
    """An explicit human choice (e.g. forcing external for comparison
    testing) wins even in a verified-native session."""
    monkeypatch.setenv("VISION_ROUTING", "external")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_explicit_native_overrides_relay_base_url(monkeypatch):
    """An explicit human choice is trusted over the relay-presence signal —
    the user has more information than the base URL alone provides."""
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://my-relay.example.com/v1")
    assert vision.resolve_routing() == "native"


def test_resolve_routing_case_insensitive(monkeypatch):
    monkeypatch.setenv("VISION_ROUTING", "NATIVE")
    assert vision.resolve_routing() == "native"


def test_resolve_routing_blocklist_overrides_native(monkeypatch):
    """A known text-only model forces 'external' even if VISION_ROUTING=native
    was left over from a previous native-model session — the blocklist only
    ever pushes toward the safe direction, never the other way."""
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-chat")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_blocklist_matches_without_vision_routing_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-reasoner")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_blocklist_case_insensitive(monkeypatch):
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setenv("ANTHROPIC_MODEL", "DeepSeek-V3")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_blocklist_overrides_official_base_url(monkeypatch):
    """The blocklist wins even against a structurally-native-looking base
    URL — belt and suspenders, though this combination shouldn't arise in
    practice (a genuine Anthropic session never reports a DeepSeek model)."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-chat")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_blocklist_matches_deepseek_v4_text_models(monkeypatch):
    """DeepSeek's current text-only models (deepseek-v4-flash, deepseek-v4-pro)
    must still be blocked after carving out the new vision variant below."""
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-v4-flash")
    assert vision.resolve_routing() == "external"


def test_resolve_routing_blocklist_excludes_deepseek_vision_variant(monkeypatch):
    """deepseek-v4-flash-vision-exp is DeepSeek's dedicated vision model, not
    a text-only backend — it must not match the blocklist, so an explicit
    VISION_ROUTING=native is left standing (mirrors GLM's -v and Kimi's
    dotted k2.x exclusions)."""
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-v4-flash-vision-exp")
    assert vision.resolve_routing() == "native"


def test_resolve_routing_unrecognized_model_with_relay_does_not_imply_native(monkeypatch):
    """An unlisted model name must never be enough to infer native by
    itself — only an explicit VISION_ROUTING=native, or a verified official
    base URL, can produce 'native'."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://my-relay.example.com/v1")
    monkeypatch.setenv("ANTHROPIC_MODEL", "some-brand-new-multimodal-model")
    assert vision.resolve_routing() == "external"


# ── routing_message ──────────────────────────────────────────────────
def test_routing_message_native():
    msg = vision.routing_message("native")
    assert "native" in msg.lower()
    assert "skip" in msg.lower()


def test_routing_message_external():
    msg = vision.routing_message("external")
    assert "external" in msg.lower()


# ── cli: --check-routing / --session-start-hook ───────────────────────
def test_cli_check_routing_prints_native_by_default(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["vision.py", "--check-routing"])
    vision.main()
    assert capsys.readouterr().out.strip() == "native"


def test_cli_check_routing_prints_external_with_relay_base_url(monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://my-relay.example.com/v1")
    monkeypatch.setattr(sys, "argv", ["vision.py", "--check-routing"])
    vision.main()
    assert capsys.readouterr().out.strip() == "external"


def test_cli_check_routing_prints_native(monkeypatch, capsys):
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setattr(sys, "argv", ["vision.py", "--check-routing"])
    vision.main()
    assert capsys.readouterr().out.strip() == "native"


def test_cli_session_start_hook_emits_valid_json(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["vision.py", "--session-start-hook"])
    vision.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "native" in payload["hookSpecificOutput"]["additionalContext"].lower()


def test_cli_session_start_hook_reflects_native_routing(monkeypatch, capsys):
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setattr(sys, "argv", ["vision.py", "--session-start-hook"])
    vision.main()
    payload = json.loads(capsys.readouterr().out)
    assert "native" in payload["hookSpecificOutput"]["additionalContext"].lower()


def test_cli_native_routing_skips_without_image_args(monkeypatch, capsys):
    """With VISION_ROUTING=native and no image_path/prompt given, main() must
    short-circuit on the routing check before reaching the required-args
    validation — the whole point is that no image analysis is attempted."""
    monkeypatch.setenv("VISION_ROUTING", "native")
    monkeypatch.setattr(sys, "argv", ["vision.py"])
    vision.main()
    assert "native" in capsys.readouterr().out.lower()


# ── resolve_provider ─────────────────────────────────────────────────
def test_resolve_provider_explicit_valid():
    name, config = vision.resolve_provider("qwen")
    assert name == "qwen"
    assert config == vision.PROVIDERS["qwen"]


def test_resolve_provider_explicit_deepseek():
    name, config = vision.resolve_provider("deepseek")
    assert name == "deepseek"
    assert config == {
        "key_env": "DEEPSEEK_API_KEY",
        "base_env": "DEEPSEEK_BASE_URL",
        "base_default": "https://api.deepseek.com",
        "model_default": "deepseek-v4-flash-vision-exp",
        "protocol": "openai",
    }


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


# ── resolve_provider: custom / dynamic providers ─────────────────────
def test_resolve_provider_custom_synthesizes_from_env(monkeypatch):
    monkeypatch.setenv("MYAPI_BASE_URL", "https://my-endpoint.test/v1")
    monkeypatch.setenv("MYAPI_MODEL", "my-vision-model")

    name, config = vision.resolve_provider("myapi")

    assert name == "myapi"
    assert config == {
        "key_env": "MYAPI_API_KEY",
        "base_env": "MYAPI_BASE_URL",
        "base_default": "https://my-endpoint.test/v1",
        "model_default": "my-vision-model",
        "protocol": "openai",
    }


def test_resolve_provider_custom_via_vision_provider_env(monkeypatch):
    monkeypatch.setenv("VISION_PROVIDER", "myapi")
    monkeypatch.setenv("MYAPI_BASE_URL", "https://my-endpoint.test/v1")
    monkeypatch.setenv("MYAPI_MODEL", "my-vision-model")

    name, config = vision.resolve_provider(None)

    assert name == "myapi"
    assert config["base_default"] == "https://my-endpoint.test/v1"


def test_resolve_provider_custom_name_is_lowercased(monkeypatch):
    monkeypatch.setenv("MYAPI_BASE_URL", "https://my-endpoint.test/v1")
    monkeypatch.setenv("MYAPI_MODEL", "my-vision-model")

    name, _ = vision.resolve_provider("MyApi")

    assert name == "myapi"


def test_resolve_provider_custom_anthropic_protocol(monkeypatch):
    monkeypatch.setenv("MYAPI_BASE_URL", "https://my-endpoint.test")
    monkeypatch.setenv("MYAPI_MODEL", "claude-like-model")
    monkeypatch.setenv("MYAPI_PROTOCOL", "anthropic")

    _, config = vision.resolve_provider("myapi")

    assert config["protocol"] == "anthropic"


def test_resolve_provider_custom_invalid_protocol_exits(monkeypatch):
    monkeypatch.setenv("MYAPI_BASE_URL", "https://my-endpoint.test")
    monkeypatch.setenv("MYAPI_MODEL", "some-model")
    monkeypatch.setenv("MYAPI_PROTOCOL", "not-a-real-protocol")

    with pytest.raises(SystemExit):
        vision.resolve_provider("myapi")


def test_resolve_provider_custom_missing_base_url_exits(monkeypatch):
    monkeypatch.setenv("MYAPI_MODEL", "some-model")

    with pytest.raises(SystemExit):
        vision.resolve_provider("myapi")


def test_resolve_provider_custom_missing_model_exits(monkeypatch):
    monkeypatch.setenv("MYAPI_BASE_URL", "https://my-endpoint.test")

    with pytest.raises(SystemExit):
        vision.resolve_provider("myapi")


def test_resolve_provider_custom_missing_everything_exits(monkeypatch):
    with pytest.raises(SystemExit):
        vision.resolve_provider("totally-unconfigured")


def test_resolve_provider_custom_model_satisfied_by_global_vision_model(monkeypatch):
    monkeypatch.setenv("MYAPI_BASE_URL", "https://my-endpoint.test")
    monkeypatch.setenv("VISION_MODEL", "global-model")

    name, config = vision.resolve_provider("myapi")

    assert name == "myapi"
    assert config["model_default"] == "global-model"


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


def test_vision_dispatches_by_protocol_field_not_provider_name(monkeypatch, tmp_path):
    """A custom provider named e.g. 'myapi' with protocol=anthropic must still
    dispatch to the anthropic request shape — dispatch is data-driven, not
    keyed off the literal string 'anthropic'."""
    image_path = tmp_path / "shot.png"
    image_path.write_bytes(b"fake-png-bytes")

    called = {}

    def fake_vision_anthropic(*args, **kwargs):
        called["yes"] = True
        return "ok"

    monkeypatch.setattr(vision, "vision_anthropic", fake_vision_anthropic)
    custom_config = {
        "key_env": "MYAPI_API_KEY",
        "base_env": "MYAPI_BASE_URL",
        "base_default": "https://my-endpoint.test",
        "model_default": "claude-like-model",
        "protocol": "anthropic",
    }
    result = vision.vision(str(image_path), "p", "myapi", custom_config)

    assert result == "ok"
    assert called.get("yes") is True
