"""
Multi-provider video analysis tool.
Extracts key frames from video, sends each to vision model for description.

Usage: python video.py [--provider <name>] [--frames N] <video_path> <prompt>

Providers: doubao (豆包), qwen (通义千问), openai, gemini
Set one of: DOUBAO_API_KEY, DASHSCOPE_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
"""
import sys
import os
import base64
import argparse
import tempfile
import shutil
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
    "gemini": {
        "key_env": "GEMINI_API_KEY",
        "base_env": "GEMINI_BASE_URL",
        "base_default": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model_default": "gemini-2.5-flash",
    },
}

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}


# ── helpers ─────────────────────────────────────────────────────────
def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def resolve_provider(name: str | None) -> tuple[str, dict]:
    if name:
        if name not in PROVIDERS:
            names = ", ".join(PROVIDERS)
            print(f"Error: unknown provider '{name}'. Available: {names}", file=sys.stderr)
            sys.exit(1)
        return name, PROVIDERS[name]

    env_provider = os.environ.get("VISION_PROVIDER", "").lower()
    if env_provider:
        if env_provider not in PROVIDERS:
            names = ", ".join(PROVIDERS)
            print(f"Error: VISION_PROVIDER='{env_provider}' is invalid. Available: {names}", file=sys.stderr)
            sys.exit(1)
        return env_provider, PROVIDERS[env_provider]

    for pname, pconf in PROVIDERS.items():
        if os.environ.get(pconf["key_env"]):
            return pname, pconf

    return "doubao", PROVIDERS["doubao"]


def resolve_model(provider_name: str, config: dict) -> str:
    global_model = os.environ.get("VISION_MODEL", "")
    if global_model:
        return global_model
    provider_model_env = f"{provider_name.upper()}_MODEL"
    provider_model = os.environ.get(provider_model_env, "")
    if provider_model:
        return provider_model
    return config["model_default"]


def ask_vision(image_path: str, prompt: str, provider_name: str, config: dict) -> str:
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


def extract_frames(video_path: str, num_frames: int, tmp_dir: str) -> list[str]:
    """Extract evenly-spaced key frames from video, return list of frame image paths."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total / fps if fps > 0 else 0

    if total == 0:
        cap.release()
        print("Error: cannot read video frames", file=sys.stderr)
        sys.exit(1)

    actual_frames = min(num_frames, total)
    step = total // actual_frames if actual_frames > 0 else 1

    frames = []
    for i in range(actual_frames):
        frame_idx = min(i * step, total - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            frame_path = os.path.join(tmp_dir, f"frame_{i:04d}.jpg")
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames.append(frame_path)
            timestamp = frame_idx / fps if fps > 0 else 0
            print(f"  [frame {i+1}/{actual_frames}] t={timestamp:.1f}s", file=sys.stderr)

    cap.release()
    return frames


# ── main ────────────────────────────────────────────────────────────
def analyze_video(video_path: str, prompt: str, provider_name: str, config: dict,
                  num_frames: int = 5) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="video_frames_")
    try:
        print(f"Extracting {num_frames} frames from video...", file=sys.stderr)
        frames = extract_frames(video_path, num_frames, tmp_dir)

        if not frames:
            return "Error: no frames extracted from video."

        print(f"Analyzing {len(frames)} frames with {provider_name}...", file=sys.stderr)

        results = []
        for i, frame_path in enumerate(frames):
            frame_prompt = (
                f"{prompt}\n\n[This is frame {i+1} of {len(frames)} from the video. "
                f"Describe what you see in this frame.]"
            )
            desc = ask_vision(frame_path, frame_prompt, provider_name, config)
            results.append(f"--- Frame {i+1}/{len(frames)} ---\n{desc}")

        # summary
        print(f"Asking {provider_name} for video-level summary...", file=sys.stderr)
        combined = "\n\n".join(results)
        summary_prompt = (
            f"Based on these frame-by-frame descriptions from a video, "
            f"write a concise summary of what happens in the video:\n\n{combined}"
        )
        summary = ask_vision(frames[0], summary_prompt, provider_name, config)

        output = f"=== Video Summary ===\n{summary}\n\n=== Frame-by-Frame ===\n{combined}"
        return output

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── cli ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Multi-provider video analysis tool (frame-based)"
    )
    parser.add_argument("--provider", "-p", choices=list(PROVIDERS), default=None,
                        help="Vision model provider (auto-detected from env if omitted)")
    parser.add_argument("--frames", "-n", type=int, default=5,
                        help="Number of frames to extract (default: 5)")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("prompt", help="What to look for in the video")
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Error: file not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)

    ext = Path(args.video_path).suffix.lower()
    if ext not in VIDEO_EXTS:
        print(f"Warning: '{ext}' may not be a supported video format", file=sys.stderr)

    provider_name, config = resolve_provider(args.provider)

    try:
        result = analyze_video(args.video_path, args.prompt, provider_name, config, args.frames)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
