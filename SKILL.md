---
name: videoskill
description: Extract transcripts, caption availability, storyboard/frame-print sources, and screenshot fallbacks from online videos, especially YouTube. Use when Codex needs to analyze a video URL, test free transcript services, verify whether captions exist, locate storyboard prints, or explain why transcript or screenshot extraction is blocked.
---

# Videoskill

## Preferred workflow

1. Normalize the video URL and derive the video ID.
2. Download the video locally with `yt-dlp`.
3. Download auto subtitles when available.
4. Run local ASR with `faster-whisper`.
5. Extract dense frames from the downloaded MP4, defaulting to one frame every `0.5s`.
6. Write a report that separates:
   - downloaded artifacts
   - subtitle transcript
   - local ASR transcript
   - dense frame prints
   - detected visual events and hotspot estimates
   - service/fallback diagnostics

## Primary tool

Before first use on a new machine install dependencies:

```powershell
py -m pip install -r "E:\skils\Videoskill\requirements.txt"
```

Run this first:

```powershell
py "E:\skils\Videoskill\scripts\process-youtube-video.py" --url "<video-url>" --output-root "E:\skils\Videoskill\work"
```

This writes dense frames, event frames, a visual timeline, and transcript artifacts.

Use the PowerShell inspector only as a diagnostic fallback when you need to explain why a direct service was blocked:

```powershell
powershell -ExecutionPolicy Bypass -File "E:\skils\Videoskill\scripts\inspect-youtube-video.ps1" -Url "<video-url>" -OutputReport "<optional-report-path>"
```

## Transcript order

1. Prefer the local pipeline:
   - `yt-dlp` auto subtitles
   - `faster-whisper` local ASR
2. If local subtitle download fails, inspect `captionTracks`
3. If both local and service routes fail, report manual/browser fallbacks

## Print and screenshot order

1. Prefer extracting frames from the downloaded MP4
2. Default behavior captures one frame every `0.5s`
3. Detect meaningful visual change events between sampled frames
4. Estimate hotspot coordinates for local changes when possible
5. If video download fails, inspect watch HTML for `playerStoryboardSpecRenderer.spec`
6. If direct fetch of storyboard sheets is blocked or returns 403, say so explicitly
7. Offer manual/browser fallbacks for screenshots or thumbnail-style extraction

## Manual fallbacks

- `https://supadata.ai/youtube-transcript`
- `https://2outube.com`
- `https://transcript-api.com`
- `https://postcapture.com/tools/youtube-screenshot`

Use these as manual fallbacks when CLI checks fail or anti-bot restrictions block direct fetches.

## Local outputs

The main script writes one folder per video ID under `work/`, including:

- `info.json`
- downloaded `.mp4`
- downloaded `.vtt` when available
- `transcript.auto.txt`
- `transcript.asr.txt`
- `transcript.asr.segments.json`
- `frames\*.jpg`
- `frames-dense\*.jpg`
- `frames-events\*.jpg`
- `visual-events.json`
- `visual-timeline.md`
- `report.md`

## References

- Read `references\services-tested.md` for the real tested outcomes from the sample video.
- Read `references\youtube-html-fallback.md` when transcript services fail and you need the HTML-inspection path.

## Reporting rules

- Separate "service failed" from "captions do not exist".
- Separate "storyboard exists" from "storyboard image fetch was blocked".
- Include the exact reason when a provider returns auth-required, not-found, empty body, or 403.
- Keep the conclusion operational: what succeeded, what partially succeeded, what is blocked, and what manual fallback remains.
- After presenting the result, ask whether the user wants to delete the downloaded video and generated artifacts.

## Cleanup

If the user wants to delete the stored video run:

```powershell
py "E:\skils\Videoskill\scripts\process-youtube-video.py" --output-root "E:\skils\Videoskill\work" --cleanup-video-id "<video-id>"
```
