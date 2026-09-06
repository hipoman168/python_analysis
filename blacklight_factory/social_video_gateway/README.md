# DAYONG Social Video Gateway — Phase 1

Status: IMPLEMENTED_ON_BRANCH / RUNTIME_ACCEPTANCE_PENDING
Owner: CEO-002
Purpose: external-video learning ingress only. No republishing automation in Phase 1.

## Goal

User pastes a public social-video URL. The gateway identifies the platform, resolves the source through a reuse-first extractor chain, preserves provenance, and produces media/transcript inputs for the downstream Skill Seekers knowledge-ingestion pipeline.

## Reuse-first extractor order

- YouTube: yt-dlp -> Cobalt fallback
- Facebook: yt-dlp -> authenticated yt-dlp/browser-cookie path -> Cobalt fallback
- Instagram: yt-dlp -> authenticated yt-dlp/browser-cookie path -> Cobalt fallback
- TikTok: yt-dlp -> Cobalt fallback
- Douyin: yt-dlp first, then platform-specific resolver adapter when required
- Generic supported URL: yt-dlp -> Cobalt fallback

`gallery-dl` is reserved for image/carousel posts and is not the primary video engine.

## Phase 1 data flow

URL -> platform detection -> resolver/extractor -> local media or subtitle -> transcript (subtitle first; Whisper fallback) -> metadata/provenance manifest -> Skill Seekers local-video pipeline -> DAYONG Knowledge Layer.

## Safety and rights boundary

Phase 1 is a learning/research ingestion path. It must not bypass private-account access controls, paywalls, deleted-content restrictions, or other access controls. Source URL and acquisition method must be preserved in evidence. Repurposing/republication belongs to Phase 2 and requires a separate rights/policy gate.

## Runtime acceptance

A Phase 1 PASS requires real evidence for all of the following:

1. Public Facebook Reel/share URL accepted.
2. At least one actual media/subtitle artifact obtained without manual download/format conversion.
3. Transcript produced (native subtitle or Whisper fallback).
4. Source URL, platform, extractor used and timestamps preserved.
5. Output accepted by Skill Seekers/local-video ingestion.
6. Same source can be queried by at least two governed agents.
7. Failure/access restrictions recorded instead of silently bypassed.

No PASS claim until runtime evidence exists.
