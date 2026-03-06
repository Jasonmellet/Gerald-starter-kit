#!/usr/bin/env python3
"""
Phase 1 YouTube ingest helper for Gerald's workspace.

Uses yt-dlp to fetch video metadata and captions/subtitles only.
No audio download or transcription. Run from agent-lab directory:

  python3 tools/youtube_ingest.py "https://www.youtube.com/watch?v=..."

Writes:
  sources/<slug>_metadata.json
  sources/<slug>_transcript.txt

Fails clearly if captions are unavailable (no Phase 1 fallback).
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Workspace root: parent of tools/
TOOLS_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = TOOLS_DIR.parent
SOURCES_DIR = WORKSPACE_ROOT / "sources"
# Prefer local binary in tools/ (yt-dlp_macos on macOS, yt-dlp elsewhere), else system yt-dlp
import sys
if sys.platform == "darwin" and (TOOLS_DIR / "yt-dlp_macos").is_file():
    YT_DLP = TOOLS_DIR / "yt-dlp_macos"
elif (TOOLS_DIR / "yt-dlp").is_file():
    YT_DLP = TOOLS_DIR / "yt-dlp"
else:
    YT_DLP = None  # use "yt-dlp" from PATH


def slugify(s: str, max_len: int = 80) -> str:
    """Safe filename slug from title."""
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:max_len] or "video"


def run_ytdlp(args: list[str]) -> subprocess.CompletedProcess:
    """Run yt-dlp; use local binary in tools/ if present, else PATH."""
    yt_dlp_bin = str(YT_DLP) if YT_DLP else "yt-dlp"
    try:
        return subprocess.run(
            [yt_dlp_bin, *args],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        print("Error: yt-dlp not found. Install with: brew install yt-dlp", file=sys.stderr)
        sys.exit(1)


def get_metadata(url: str) -> dict:
    """Fetch video metadata as JSON (no download)."""
    proc = run_ytdlp([
        "--dump-json",
        "--no-download",
        "--no-warnings",
        url,
    ])
    if proc.returncode != 0:
        print(f"Error: yt-dlp failed: {proc.stderr or proc.stdout}", file=sys.stderr)
        sys.exit(1)
    return json.loads(proc.stdout)


def get_captions(url: str, prefer_lang: str = "en") -> Optional[str]:
    """
    Try to get subtitles/captions. Prefer manual, then auto.
    Returns transcript text or None if unavailable.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out_tpl = str(Path(tmp) / "sub")
        proc = run_ytdlp([
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "en.*,en",
            "--skip-download",
            "--no-warnings",
            "--sub-format", "srt/best",
            "--convert-subs", "srt",
            "--output", out_tpl + ".%(ext)s",
            url,
        ])
        if proc.returncode != 0:
            return None
        # Find written sub file
        sub_files = list(Path(tmp).glob("*.srt"))
        if not sub_files:
            return None
        return sub_files[0].read_text(encoding="utf-8", errors="replace")


def srt_to_plain(srt: str) -> str:
    """Strip SRT timestamps and keep dialogue lines."""
    lines = []
    for line in srt.splitlines():
        line = line.strip()
        if not line or line.isdigit() or " --> " in line:
            continue
        lines.append(line)
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 tools/youtube_ingest.py <youtube_url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1].strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        print("Error: URL does not look like YouTube.", file=sys.stderr)
        sys.exit(1)

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching metadata...")
    info = get_metadata(url)
    title = info.get("title") or "unknown"
    uploader = info.get("uploader") or info.get("channel") or ""
    upload_date = info.get("upload_date") or ""

    slug = slugify(title)
    # Avoid overwriting different videos with same title
    video_id = info.get("id") or ""
    if video_id:
        slug = f"{slug}_{video_id}"[:90]

    print("Fetching captions (en preferred)...")
    raw_captions = get_captions(url)
    if not raw_captions:
        print("Error: No captions/subtitles available for this video. Phase 1 does not support audio transcription.", file=sys.stderr)
        sys.exit(1)

    transcript = srt_to_plain(raw_captions)
    if not transcript.strip():
        print("Error: Captions were empty after conversion.", file=sys.stderr)
        sys.exit(1)

    meta_out = {
        "title": title,
        "url": url,
        "channel": uploader,
        "upload_date": upload_date,
        "id": video_id,
        "slug": slug,
    }

    meta_path = SOURCES_DIR / f"{slug}_metadata.json"
    meta_path.write_text(json.dumps(meta_out, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")

    trans_path = SOURCES_DIR / f"{slug}_transcript.txt"
    trans_path.write_text(transcript, encoding="utf-8")
    print(f"Wrote {trans_path}")

    print("Done. Gerald can read these files and write an analysis to outputs/.")


if __name__ == "__main__":
    main()
