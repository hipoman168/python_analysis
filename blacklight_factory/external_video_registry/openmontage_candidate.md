# OpenMontage Candidate Registry

Status: HIGH_PRIORITY_SANDBOX_CANDIDATE
Registered: 2026-09-08
Owner: CEO-002
Source: https://github.com/calesthio/OpenMontage
Website: https://openmontage.video/
License: GNU AGPLv3 (upstream main repository)

## Why this matters to DAYONG

OpenMontage is directly aligned with the DAYONG Social Video / Travel Video production objective. The upstream project supports reference-video ingestion from YouTube / Short / Reel / TikTok / local video, analysis of transcript / pacing / scenes / keyframes / style, generation of multiple differentiated concepts, storyboard approval gates, asset generation, TTS, subtitles, Remotion/FFmpeg composition, and post-render quality checks.

Upstream currently describes 12 production pipelines, 100+ tools, and 700+ agent skill / production-knowledge files. It supports local/offline components and optional external model providers.

## Reuse-first decision

Decision order: Fork/Adapt or Wrap/Integrate before building equivalent video-production orchestration from scratch.

Recommended DAYONG role:

Social URL / local reference video
→ DAYONG Social Video Gateway
→ OpenMontage analysis / production pipeline
→ DAYONG storyboard Approval Gate
→ local/API asset generation
→ Remotion / HyperFrames / FFmpeg render
→ DAYONG QC / Evidence
→ Social Publisher

## Important license boundary

The upstream canonical repository is GNU AGPLv3. Do not copy upstream source directly into proprietary DAYONG modules until license/compliance review is complete. Prefer an isolated external service/process boundary or upstream-compatible deployment during sandbox evaluation.

## Sandbox acceptance gates

1. Installability on Node-02 or isolated Linux/Windows sandbox.
2. Reference URL ingestion from a user-provided short-video fixture.
3. Transcript / pacing / scene / keyframe extraction evidence.
4. Storyboard / approval-gate evidence before render.
5. At least one zero/low-paid-provider render path.
6. Remotion or FFmpeg output validation with ffprobe.
7. Evidence of resumability / checkpointing / cost log.
8. No secret leakage; external provider credentials remain in DAYONG Credential Broker.
9. License/compliance review before production integration.

## Runtime completion rule

Do not mark integrated or production-ready until a real end-to-end video has been produced from a reference URL and passed DAYONG Runtime Evidence / QC gates.
