from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
import json
import re


class Platform(str, Enum):
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    DOUYIN = "douyin"
    THREADS = "threads"
    GENERIC = "generic"


@dataclass(frozen=True)
class ExtractionStep:
    engine: str
    authenticated: bool = False
    purpose: str = "media"


@dataclass(frozen=True)
class IngestPlan:
    source_url: str
    platform: Platform
    steps: tuple[ExtractionStep, ...]
    transcript_policy: str = "native_subtitles_first_then_whisper"
    preserve_provenance: bool = True
    phase: str = "learning_only"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["platform"] = self.platform.value
        return data


_HOST_RULES: tuple[tuple[Platform, re.Pattern[str]], ...] = (
    (Platform.YOUTUBE, re.compile(r"(^|\.)(youtube\.com|youtu\.be)$", re.I)),
    (Platform.FACEBOOK, re.compile(r"(^|\.)(facebook\.com|fb\.watch)$", re.I)),
    (Platform.INSTAGRAM, re.compile(r"(^|\.)instagram\.com$", re.I)),
    (Platform.TIKTOK, re.compile(r"(^|\.)tiktok\.com$", re.I)),
    (Platform.DOUYIN, re.compile(r"(^|\.)(douyin\.com|iesdouyin\.com)$", re.I)),
    (Platform.THREADS, re.compile(r"(^|\.)threads\.(net|com)$", re.I)),
)


def detect_platform(url: str) -> Platform:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute http(s) URL")
    host = (parsed.hostname or "").lower()
    for platform, pattern in _HOST_RULES:
        if pattern.search(host):
            return platform
    return Platform.GENERIC


def build_plan(url: str) -> IngestPlan:
    platform = detect_platform(url)

    if platform == Platform.YOUTUBE:
        steps = (
            ExtractionStep("yt-dlp", purpose="subtitle_or_media"),
            ExtractionStep("cobalt", purpose="media_fallback"),
        )
    elif platform in {Platform.FACEBOOK, Platform.INSTAGRAM}:
        steps = (
            ExtractionStep("yt-dlp", purpose="public_extract"),
            ExtractionStep("yt-dlp", authenticated=True, purpose="browser_cookie_extract"),
            ExtractionStep("cobalt", purpose="public_media_fallback"),
        )
    elif platform == Platform.TIKTOK:
        steps = (
            ExtractionStep("yt-dlp", purpose="public_extract"),
            ExtractionStep("cobalt", purpose="public_media_fallback"),
        )
    elif platform == Platform.DOUYIN:
        steps = (
            ExtractionStep("yt-dlp", purpose="public_extract"),
            ExtractionStep("douyin-resolver", purpose="platform_specific_fallback"),
        )
    elif platform == Platform.THREADS:
        steps = (
            ExtractionStep("yt-dlp", purpose="public_extract"),
            ExtractionStep("cobalt", purpose="public_media_fallback"),
        )
    else:
        steps = (
            ExtractionStep("yt-dlp", purpose="generic_extract"),
            ExtractionStep("cobalt", purpose="generic_fallback"),
        )

    return IngestPlan(source_url=url, platform=platform, steps=steps)


def write_manifest(plan: IngestPlan, output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    manifest = path / "source_manifest.json"
    manifest.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def candidate_engines(plan: IngestPlan) -> Iterable[str]:
    for step in plan.steps:
        yield step.engine


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DAYONG Social Video Gateway Phase 1 planner")
    parser.add_argument("url")
    parser.add_argument("--manifest-dir")
    args = parser.parse_args()

    ingest_plan = build_plan(args.url)
    print(json.dumps(ingest_plan.to_dict(), ensure_ascii=False, indent=2))
    if args.manifest_dir:
        print(write_manifest(ingest_plan, args.manifest_dir))
