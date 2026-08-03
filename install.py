"""
Install the vision skill to Claude Code.

Interactive mode (human):
    python install.py

CLI mode (Claude Code driven):
    python install.py --api-key qwen:sk-xxx --default-provider qwen --merge-claude

The script copies skill files, configures env vars in Claude Code settings.json,
and merges the CLAUDE.md template into the user's CLAUDE.md.
"""
import sys
import os
import json
import shutil
import argparse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent / "vision"
SKILL_FILES = ["SKILL.md", "vision.py"]
CLAUDE_TEMPLATE = Path(__file__).resolve().parent / "CLAUDE.md"

MERGE_MARKER_START = "<!-- === VISION_SKILL_START === -->"
MERGE_MARKER_END = "<!-- === VISION_SKILL_END === -->"

PROVIDER_LABELS = {
    "doubao": "Doubao (Volcengine Ark)",
    "qwen": "Qwen (DashScope)",
    "openai": "OpenAI (GPT-4o)",
    "anthropic": "Claude (Anthropic)",
}

PROVIDER_KEY_ENV = {
    "doubao": "DOUBAO_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def key_env_for(provider: str) -> str:
    """Built-in providers have a fixed key env var; anything else follows
    the {NAME}_API_KEY convention vision.py uses to synthesize providers."""
    return PROVIDER_KEY_ENV.get(provider, f"{provider.upper()}_API_KEY")


def parse_provider_value_pairs(entries: list | None, flag_name: str) -> dict:
    result = {}
    for entry in entries or []:
        if ":" not in entry:
            print(f"  skipping invalid {flag_name} '{entry}' (expected provider:value)")
            continue
        provider, value = entry.split(":", 1)
        result[provider] = value
    return result


# ── helpers ─────────────────────────────────────────────────────────
def get_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def read_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def set_env_in_settings(key: str, value: str) -> None:
    path = get_settings_path()
    settings = read_json(path)
    settings.setdefault("env", {})
    settings["env"][key] = value
    write_json(path, settings)


# ── SessionStart hook (routing) ────────────────────────────────────
HOOK_MATCHER = "startup|resume|clear|compact"


def register_session_start_hook(vision_py_path: Path, dry_run: bool = False) -> None:
    """Register a SessionStart hook so vision-routing (native vs. external) is
    recomputed from the live environment every session — no manual toggle,
    no re-running this installer after switching providers."""
    command = f'python "{vision_py_path}" --session-start-hook'

    if dry_run:
        print(f"[dry-run] register SessionStart hook -> {command}")
        return

    path = get_settings_path()
    settings = read_json(path)
    session_start = settings.setdefault("hooks", {}).setdefault("SessionStart", [])

    # drop any prior registration of this hook (path may have changed) before re-adding
    session_start[:] = [
        entry for entry in session_start
        if not any(
            h.get("type") == "command" and "--session-start-hook" in h.get("command", "")
            for h in entry.get("hooks", [])
        )
    ]
    session_start.append({
        "matcher": HOOK_MATCHER,
        "hooks": [{"type": "command", "command": command, "timeout": 10}],
    })

    write_json(path, settings)
    print("  registered SessionStart hook for vision routing")


# ── file copy ───────────────────────────────────────────────────────
def install_skill_files(target: Path, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] install skill files to {target}")
        for f in SKILL_FILES:
            print(f"[dry-run]   {SKILL_DIR / f} -> {target / f}")
        return

    target.mkdir(parents=True, exist_ok=True)
    for f in SKILL_FILES:
        shutil.copy2(SKILL_DIR / f, target / f)
        print(f"  copied {f}")


# ── CLAUDE.md merge ─────────────────────────────────────────────────
def merge_claude_md(dry_run: bool = False) -> None:
    """Merge the project CLAUDE.md template into ~/.claude/CLAUDE.md."""
    if not CLAUDE_TEMPLATE.exists():
        print("  (no CLAUDE.md template found, skipping merge)")
        return

    template_content = CLAUDE_TEMPLATE.read_text(encoding="utf-8").strip()
    marked = f"\n\n{MERGE_MARKER_START}\n{template_content}\n{MERGE_MARKER_END}"

    user_claude = Path.home() / ".claude" / "CLAUDE.md"

    if dry_run:
        print(f"[dry-run] merge CLAUDE.md -> {user_claude}")
        return

    if user_claude.exists():
        existing = user_claude.read_text(encoding="utf-8")
        if MERGE_MARKER_START in existing and MERGE_MARKER_END in existing:
            # update existing marked section
            before = existing.split(MERGE_MARKER_START)[0]
            after = existing.split(MERGE_MARKER_END)[-1]
            new_content = before + marked + after
            user_claude.write_text(new_content, encoding="utf-8")
            print("  updated CLAUDE.md (existing vision section replaced)")
        else:
            # append with markers
            user_claude.write_text(existing + marked, encoding="utf-8")
            print("  merged CLAUDE.md (appended with markers)")
    else:
        user_claude.parent.mkdir(parents=True, exist_ok=True)
        user_claude.write_text(marked.strip(), encoding="utf-8")
        print("  created CLAUDE.md")


# ── interactive mode ────────────────────────────────────────────────
def interactive() -> None:
    print("\n" + "=" * 50)
    print("  Vision Skill Installer")
    print("=" * 50 + "\n")

    # pick provider
    print("Choose vision provider(s):")
    labels = list(PROVIDER_LABELS.items())
    for i, (pid, plabel) in enumerate(labels, 1):
        print(f"  [{i}] {plabel}")
    print(f"  [{len(labels) + 1}] All of the above")
    print(f"  [{len(labels) + 2}] Custom (any OpenAI- or Anthropic-compatible endpoint)")

    custom = None
    while True:
        try:
            choice = input(f"\nChoice (1-{len(labels) + 2}) [1]: ").strip() or "1"
            idx = int(choice)
            if 1 <= idx <= len(labels):
                providers = [labels[idx - 1][0]]
                break
            elif idx == len(labels) + 1:
                providers = [p[0] for p in labels]
                break
            elif idx == len(labels) + 2:
                print("\nCustom provider:")
                pid = input("  Provider name (e.g. myapi): ").strip().lower()
                if not pid:
                    print("  Name cannot be empty.")
                    continue
                base_url = input("  Base URL: ").strip()
                model = input("  Model: ").strip()
                if not base_url or not model:
                    print("  Base URL and Model are both required.")
                    continue
                protocol = input("  Protocol (openai/anthropic) [openai]: ").strip().lower() or "openai"
                if protocol not in ("openai", "anthropic"):
                    print("  Protocol must be 'openai' or 'anthropic'.")
                    continue
                custom = {"base_url": base_url, "model": model, "protocol": protocol}
                providers = [pid]
                break
        except ValueError:
            pass
        print("Invalid choice, try again.")

    # api keys
    api_keys = {}
    for pid in providers:
        key = input(f"{key_env_for(pid)}: ").strip()
        if key:
            api_keys[pid] = key

    if not api_keys:
        print("\nNo API keys provided. You can set them later in")
        print("  ~/.claude/settings.json under the \"env\" key.")
        print("Or set environment variables directly.\n")
    else:
        for pid, key in api_keys.items():
            set_env_in_settings(key_env_for(pid), key)
            print(f"  set {key_env_for(pid)}")

    if custom:
        pid = providers[0]
        set_env_in_settings(f"{pid.upper()}_BASE_URL", custom["base_url"])
        set_env_in_settings(f"{pid.upper()}_MODEL", custom["model"])
        print(f"  set {pid.upper()}_BASE_URL")
        print(f"  set {pid.upper()}_MODEL")
        if custom["protocol"] != "openai":
            set_env_in_settings(f"{pid.upper()}_PROTOCOL", custom["protocol"])
            print(f"  set {pid.upper()}_PROTOCOL")

    # default provider
    default = None
    if len(providers) > 1:
        default = input(f"\nDefault provider [{providers[0]}]: ").strip().lower()
        if not default:
            default = providers[0]
        elif default not in PROVIDER_KEY_ENV:
            print(f"Unknown provider, using {providers[0]}")
            default = providers[0]
    else:
        default = providers[0]

    set_env_in_settings("VISION_PROVIDER", default)
    print(f"  set VISION_PROVIDER={default}")

    # do install
    target = Path.home() / ".claude" / "skills" / "vision"
    print()
    install_skill_files(target)
    register_session_start_hook(target / "vision.py")

    # merge claude.md
    yn = input("\nMerge CLAUDE.md template into ~/.claude/CLAUDE.md? [Y/n]: ").strip().lower()
    if yn != "n":
        merge_claude_md()

    print("\nDone! The vision skill is ready.\n")


# ── non-interactive (Claude Code driven) ────────────────────────────
def run_noninteractive(args) -> None:
    dry = args.dry_run
    target = Path.home() / ".claude" / "skills" / "vision"

    # 1. copy skill files
    print("Installing vision skill files...")
    install_skill_files(target, dry_run=dry)
    print(f"  -> {target}\n")

    print("Registering SessionStart routing hook...")
    register_session_start_hook(target / "vision.py", dry_run=dry)
    print()

    # 2. configure API keys, and (for custom providers) base URL / model / protocol
    key_pairs = parse_provider_value_pairs(args.api_key, "--api-key")
    base_url_pairs = parse_provider_value_pairs(args.base_url, "--base-url")
    model_pairs = parse_provider_value_pairs(args.model, "--model")
    protocol_pairs = parse_provider_value_pairs(args.protocol, "--protocol")

    if key_pairs:
        print("Configuring API keys...")
        for provider, key in key_pairs.items():
            key_env = key_env_for(provider)
            if dry:
                print(f"  [dry-run] set {key_env} in settings.json")
            else:
                set_env_in_settings(key_env, key)
                print(f"  set {key_env} in settings.json")
        print()

    for pairs, suffix, label in (
        (base_url_pairs, "BASE_URL", "base URLs"),
        (model_pairs, "MODEL", "models"),
        (protocol_pairs, "PROTOCOL", "protocols"),
    ):
        if not pairs:
            continue
        print(f"Configuring {label}...")
        for provider, value in pairs.items():
            env_name = f"{provider.upper()}_{suffix}"
            if dry:
                print(f"  [dry-run] set {env_name} in settings.json")
            else:
                set_env_in_settings(env_name, value)
                print(f"  set {env_name} in settings.json")
        print()

    # 3. default provider (any name — built-in or custom; vision.py validates at runtime)
    if args.default_provider:
        provider = args.default_provider.lower()
        if dry:
            print(f"[dry-run] set VISION_PROVIDER={provider} in settings.json\n")
        else:
            set_env_in_settings("VISION_PROVIDER", provider)
            print(f"Default provider: {provider}")
            print(f"  set VISION_PROVIDER={provider} in settings.json\n")

    # 4. merge CLAUDE.md (only with explicit flag)
    if args.merge_claude:
        print("Merging CLAUDE.md...")
        merge_claude_md(dry_run=dry)
        print()

    if dry:
        print("[dry-run] All steps previewed above. No changes made.\n")
    else:
        print("Done.\n")


# ── cli ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Install the vision skill for Claude Code"
    )
    parser.add_argument("--api-key", action="append", metavar="PROVIDER:KEY",
                        help="API key (repeatable). E.g. --api-key qwen:sk-xxx")
    parser.add_argument("--base-url", action="append", metavar="PROVIDER:URL",
                        help="Custom provider base URL (repeatable). E.g. --base-url myapi:https://host/v1")
    parser.add_argument("--model", action="append", metavar="PROVIDER:MODEL",
                        help="Custom provider model (repeatable). E.g. --model myapi:my-vision-model")
    parser.add_argument("--protocol", action="append", metavar="PROVIDER:openai|anthropic",
                        help="Custom provider request shape (repeatable, default openai). "
                             "E.g. --protocol myapi:anthropic")
    parser.add_argument("--default-provider", metavar="PROVIDER",
                        help="Set default vision provider (built-in or custom name)")
    parser.add_argument("--merge-claude", action="store_true",
                        help="Merge CLAUDE.md template into ~/.claude/CLAUDE.md")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")
    args = parser.parse_args()

    if not SKILL_DIR.exists():
        print(f"Error: skill source not found at {SKILL_DIR}", file=sys.stderr)
        sys.exit(1)

    # Detect mode: interactive if no actionable flags and stdin is a tty
    has_cli_flags = (
        args.api_key or args.base_url or args.model or args.protocol
        or args.default_provider or args.merge_claude
    )
    if has_cli_flags or not sys.stdin.isatty():
        run_noninteractive(args)
    else:
        interactive()


if __name__ == "__main__":
    main()
