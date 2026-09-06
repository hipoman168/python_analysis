# Skill Seekers — Blacklight Factory Candidate

Status: DISCOVERY_COMPLETE / SANDBOX_POC_PENDING
Date: 2026-09-06
Upstream: yusufkaraaslan/Skill_Seekers
License: MIT

## Why this matters

Candidate core component for a Blacklight Factory knowledge-ingestion layer. It converts heterogeneous sources into AI Skills / RAG / vector-ready knowledge assets and supports multiple LLM targets.

## Verified upstream capabilities

- Python 3.10+
- MIT licensed
- 18 source types documented upstream
- 22 packaging/export targets documented upstream
- OpenAI, Gemini, Claude, DeepSeek, Qwen, Kimi targets
- MCP server with 40 tools
- stdio + HTTP MCP transports
- video optional dependencies include yt-dlp, youtube-transcript-api
- video-full adds faster-whisper, scene detection, OpenCV, OCR path
- local video files supported
- current source-type enum explicitly models YouTube, Vimeo, local file, local directory

## Important gap for DAYONG

Current upstream video source detection is explicitly YouTube / Vimeo / local file/directory. Facebook and Instagram are not first-class source types in the inspected implementation.

However the project already depends on yt-dlp for video metadata. This makes a DAYONG social-video adapter technically plausible without rebuilding the downstream knowledge pipeline.

Target architecture:

Social URL (FB/IG/Threads/YouTube/etc.)
→ DAYONG source adapter / governed downloader
→ local media + metadata + subtitles/transcript
→ Skill Seekers video/local-file pipeline
→ structured knowledge asset
→ DAYONG Knowledge Layer
→ 002 / D1 / D2 / G1

## Sandbox acceptance target

Use one non-sensitive social-video example and require evidence for:
1. source acquisition
2. transcript extraction or Whisper fallback
3. metadata preservation
4. Skill Seekers conversion
5. export to at least OpenAI + Gemini compatible targets
6. same-source Q&A by two different agents
7. provenance/source URL retained
8. failure modes and access restrictions recorded

No production installation until sandbox evidence passes the AI Engineering Gate.
