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
    "doubao": "豆包 (Doubao)",
    "qwen": "通义千问 (Qwen)",
    "openai": "OpenAI (GPT-4o)",
}

PROVIDER_KEY_ENV = {
    "doubao": "DOUBAO_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "openai": "OPENAI_API_KEY",
}


# ── helpers ─────────────────────────────────────────────────────────
def get_settings_path(user: bool = True) -> Path:
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


def set_env_in_settings(key: str, value: str, user: bool = True) -> None:
    path = get_settings_path(user)
    settings = read_json(path)
    settings.setdefault("env", {})
    settings["env"][key] = value
    write_json(path, settings)


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
    print(f"  [{len(labels) + 1}] All three")

    while True:
        try:
            choice = input(f"\nChoice (1-{len(labels) + 1}) [1]: ").strip() or "1"
            idx = int(choice)
            if 1 <= idx <= len(labels):
                providers = [labels[idx - 1][0]]
                break
            elif idx == len(labels) + 1:
                providers = [p[0] for p in labels]
                break
        except ValueError:
            pass
        print("Invalid choice, try again.")

    # api keys
    api_keys = {}
    for pid in providers:
        key_env = PROVIDER_KEY_ENV[pid]
        key = input(f"{key_env}: ").strip()
        if key:
            api_keys[pid] = key

    if not api_keys:
        print("\nNo API keys provided. You can set them later in")
        print("  ~/.claude/settings.json under the \"env\" key.")
        print("Or set environment variables directly.\n")
    else:
        for pid, key in api_keys.items():
            set_env_in_settings(PROVIDER_KEY_ENV[pid], key)
            print(f"  set {PROVIDER_KEY_ENV[pid]}")

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

    # install target
    print("\nInstall target:")
    print("  [1] User scope  (~/.claude/skills/vision/)")
    print("  [2] This project (.claude/skills/vision/)")
    choice = input("Choice [1]: ").strip() or "1"

    if choice == "2":
        cwd = Path.cwd()
        target = cwd / ".claude" / "skills" / "vision"
    else:
        target = Path.home() / ".claude" / "skills" / "vision"

    # do install
    print()
    install_skill_files(target)

    # merge claude.md
    yn = input("\nMerge CLAUDE.md template into ~/.claude/CLAUDE.md? [Y/n]: ").strip().lower()
    if yn != "n":
        merge_claude_md()

    print("\nDone! The vision skill is ready.\n")


# ── non-interactive (Claude Code driven) ────────────────────────────
def run_noninteractive(args) -> None:
    dry = args.dry_run

    # determine target
    if args.project:
        target = Path(args.project).resolve() / ".claude" / "skills" / "vision"
    else:
        target = Path.home() / ".claude" / "skills" / "vision"

    # 1. copy skill files
    print("Installing vision skill files...")
    install_skill_files(target, dry_run=dry)
    print(f"  -> {target}\n")

    # 2. configure API keys
    if args.api_key:
        print("Configuring API keys...")
        for entry in args.api_key:
            if ":" not in entry:
                print(f"  skipping invalid --api-key '{entry}' (expected provider:key)")
                continue
            provider, key = entry.split(":", 1)
            if provider not in PROVIDER_KEY_ENV:
                print(f"  skipping unknown provider '{provider}'")
                continue
            key_env = PROVIDER_KEY_ENV[provider]
            if dry:
                print(f"  [dry-run] set {key_env} in settings.json")
            else:
                set_env_in_settings(key_env, key)
                print(f"  set {key_env} in settings.json")
        print()

    # 3. default provider
    if args.default_provider:
        provider = args.default_provider.lower()
        if provider in PROVIDER_KEY_ENV:
            if dry:
                print(f"[dry-run] set VISION_PROVIDER={provider} in settings.json\n")
            else:
                set_env_in_settings("VISION_PROVIDER", provider)
                print(f"Default provider: {provider}")
                print(f"  set VISION_PROVIDER={provider} in settings.json\n")
        else:
            print(f"Unknown provider '{provider}', skipping VISION_PROVIDER\n")

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
    parser.add_argument("--default-provider", metavar="PROVIDER",
                        choices=list(PROVIDER_KEY_ENV),
                        help="Set default vision provider")
    parser.add_argument("--merge-claude", action="store_true",
                        help="Merge CLAUDE.md template into ~/.claude/CLAUDE.md")
    parser.add_argument("--project", metavar="PATH",
                        help="Install to project scope instead of user scope")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")
    args = parser.parse_args()

    if not SKILL_DIR.exists():
        print(f"Error: skill source not found at {SKILL_DIR}", file=sys.stderr)
        sys.exit(1)

    # Detect mode: interactive if no actionable flags and stdin is a tty
    has_cli_flags = args.api_key or args.default_provider or args.merge_claude or args.project
    if has_cli_flags or not sys.stdin.isatty():
        run_noninteractive(args)
    else:
        interactive()


if __name__ == "__main__":
    main()
