"""
Install the vision skill to Claude Code.
Usage:
    python install.py              # install to user scope (~/.claude/skills/vision/)
    python install.py --project .  # install to project scope (.claude/skills/vision/)
    python install.py --dry-run    # preview without writing
"""
import sys
import os
import shutil
import argparse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent / "vision"
FILES = ["SKILL.md", "vision.py"]

HELP_TEXT = """
Installation complete!

Next steps:

1. Set your API key (one of):
   - Doubao:   set DOUBAO_API_KEY=your_key
   - Qwen:     set DASHSCOPE_API_KEY=your_key
   - OpenAI:   set OPENAI_API_KEY=your_key

2. (Optional) Set default provider:
   set VISION_PROVIDER=qwen

3. (Optional) Merge CLAUDE.md into your ~/.claude/CLAUDE.md
   for automatic vision-based UI review workflows.

For PowerShell, use: $env:VAR_NAME="value"
"""


def install(target: Path, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] would install to: {target}")
        for f in FILES:
            src = SKILL_DIR / f
            print(f"[dry-run]   copy {src} -> {target / f}")
        return

    target.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        src = SKILL_DIR / f
        dst = target / f
        shutil.copy2(src, dst)
        print(f"  copied {f}")

    print(f"\nInstalled to {target}")


def main():
    default_user = Path.home() / ".claude" / "skills" / "vision"

    parser = argparse.ArgumentParser(description="Install the vision skill for Claude Code")
    parser.add_argument("--user", action="store_true", default=True,
                        help=f"Install to user scope (default: {default_user})")
    parser.add_argument("--project", type=str, metavar="PATH",
                        help="Install to project scope (e.g. --project . for current dir)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")
    args = parser.parse_args()

    if args.project:
        target = Path(args.project).resolve() / ".claude" / "skills" / "vision"
    else:
        target = default_user

    if not SKILL_DIR.exists():
        print(f"Error: skill source not found at {SKILL_DIR}", file=sys.stderr)
        sys.exit(1)

    install(target, dry_run=args.dry_run)

    if not args.dry_run:
        print(HELP_TEXT)


if __name__ == "__main__":
    main()
