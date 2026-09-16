"""
app/utils/youtube.py

Extracts the 11-character YouTube Video ID from any supported URL format.

Supported formats:
  - https://www.youtube.com/watch?v=dQw4w9WgXcQ
  - https://youtu.be/dQw4w9WgXcQ
  - https://youtube.com/watch?v=dQw4w9WgXcQ&t=30s
  - https://www.youtube.com/embed/dQw4w9WgXcQ
  - https://www.youtube.com/shorts/dQw4w9WgXcQ
"""

import re
from typing import Optional

# ── Compiled regex ─────────────────────────────────────────────────────────────
# Captures exactly 11 word-characters from any of the four known URL patterns.
_YT_RE = re.compile(
    r"(?:"
    r"youtu\.be/"                           # short link  youtu.be/VIDEO_ID
    r"|youtube\.com/(?:watch\?v=|embed/|shorts/|v/)"  # long links
    r")"
    r"([\w-]{11})",                          # capture the 11-char video ID
    re.IGNORECASE,
)


def extract_video_id(url: str) -> Optional[str]:
    """
    Return the 11-character YouTube video ID from *url*, or None if not found.

    Example
    -------
    >>> extract_video_id("https://youtu.be/dQw4w9WgXcQ")
    'dQw4w9WgXcQ'
    >>> extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s")
    'dQw4w9WgXcQ'
    """
    match = _YT_RE.search(url)
    return match.group(1) if match else None


def build_thumbnail_url(video_id: str) -> str:
    """
    Return the highest-resolution thumbnail URL for *video_id*.
    Falls back gracefully: YouTube always serves maxresdefault when available.
    """
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
