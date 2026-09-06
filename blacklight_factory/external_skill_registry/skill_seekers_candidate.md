# Skill Seekers — Blacklight Factory Candidate

Status: SANDBOX_CORE_PASS / MULTI_AGENT_ACCEPTANCE_PENDING
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

## DAYONG adapter result

Skill Seekers does not need to become a Facebook/Instagram downloader itself. DAYONG Social Video Gateway supplies a governed local-video artifact to its existing local-video path.

Runtime sample:

`https://www.facebook.com/share/r/19b56K4KxL/`

Observed chain on 2026-09-06:

Facebook share URL -> current yt-dlp -> resolved Reel/media -> video+audio download -> ffmpeg MP4 merge -> Skill Seekers local-video ingestion -> Whisper fallback -> generated SKILL.md + reference + metadata.

Evidence:

- public extraction probe run: GitHub Actions `34014087523` — PASS
- full ingest run after CLI correction: GitHub Actions `34014242318` — PASS
- artifact: `9983416218`
- `FB_MEDIA_DOWNLOAD_PASS`
- `SKILL_SEEKERS_INGEST_PASS`
- provenance manifest present
- generated `SKILL.md` present

The first tiny-Whisper output had low transcript quality, so a `small` Whisper + `zh,en` quality run was added. Transcript-quality tuning is independent of proof that the acquisition-to-knowledge pipeline functions.

## Target architecture

Social URL (FB/IG/Threads/YouTube/etc.)
→ DAYONG Social Video Gateway
→ yt-dlp / authenticated browser-cookie / Cobalt / platform resolver fallback
→ local media + provenance metadata
→ Skill Seekers local-video pipeline
→ subtitle or faster-whisper transcript
→ structured knowledge asset
→ DAYONG Knowledge Layer
→ 002 / D1 / D2 / G1

## Remaining acceptance

Core sandbox acquisition + local-video conversion is PASS for the tested public Facebook Reel. Before claiming universal social-platform support or full production acceptance, still require:

1. platform-specific runtime cases for YouTube, Instagram, TikTok and Douyin;
2. same-source Q&A by at least two governed agents;
3. access-control failures recorded rather than bypassed;
4. production storage/retention and Knowledge Layer wiring.

No claim is made that private, paywalled, deleted, or otherwise restricted content can or should be bypassed.
