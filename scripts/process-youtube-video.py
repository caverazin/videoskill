import argparse
import json
import os
import re
import shutil
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from faster_whisper import WhisperModel
from yt_dlp import YoutubeDL


def safe_slug(value: str) -> str:
    value = re.sub(r"[<>:\"/\\\\|?*]+", "-", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:120].strip() or "video"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--model", default="tiny.en")
    parser.add_argument("--sample-interval", type=float, default=0.5)
    parser.add_argument("--dense-frame-quality", type=int, default=82)
    parser.add_argument("--scene-threshold-ratio", type=float, default=0.18)
    parser.add_argument("--scene-threshold-mean", type=float, default=22.0)
    parser.add_argument("--local-threshold-ratio", type=float, default=0.012)
    parser.add_argument("--max-local-ratio", type=float, default=0.18)
    parser.add_argument("--cleanup-video-id")
    return parser.parse_args()


def cleanup_video_folder(output_root: Path, video_id: str):
    target = output_root / video_id
    if target.exists():
        shutil.rmtree(target)
        print(f"Deleted {target}")
    else:
        print(f"Nothing to delete for {video_id}")


def download_assets(url: str, output_root: Path, language: str):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    info_opts = {
        "quiet": True,
        "skip_download": True,
        "ffmpeg_location": ffmpeg_path,
    }
    with YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    video_id = info["id"]
    title = safe_slug(info.get("title") or video_id)
    out_dir = output_root / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    info_path = out_dir / "info.json"
    info_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    outtmpl = str(out_dir / f"{title} [%(id)s].%(ext)s")
    download_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": [language],
        "skip_download": False,
        "quiet": False,
        "ffmpeg_location": ffmpeg_path,
    }
    with YoutubeDL(download_opts) as ydl:
        ydl.download([url])

    mp4_files = list(out_dir.glob(f"*[{video_id}].mp4")) or list(out_dir.glob("*.mp4"))
    vtt_files = list(out_dir.glob(f"*[{video_id}].{language}.vtt")) or list(out_dir.glob(f"*.{language}.vtt"))
    return info, out_dir, mp4_files[0] if mp4_files else None, vtt_files[0] if vtt_files else None


def vtt_to_text(vtt_path: Path, output_path: Path):
    text = vtt_path.read_text(encoding="utf-8", errors="ignore")
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)
    cleaned = []
    prev = None
    for line in lines:
        if line != prev:
            cleaned.append(line)
        prev = line
    output_path.write_text("\n".join(cleaned), encoding="utf-8")


def transcribe_with_whisper(media_path: Path, output_txt: Path, output_segments: Path, model_name: str, language: str):
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(media_path), language=language, vad_filter=True)
    segment_rows = []
    transcript_lines = []
    for seg in segments:
        row = {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        }
        segment_rows.append(row)
        transcript_lines.append(f"[{seg.start:.2f} -> {seg.end:.2f}] {seg.text.strip()}")
    output_txt.write_text("\n".join(transcript_lines), encoding="utf-8")
    output_segments.write_text(
        json.dumps(
            {
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": segment_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {"language": info.language, "language_probability": info.language_probability, "duration": info.duration}


def detect_change(prev_small: np.ndarray, curr_small: np.ndarray, frame_shape, scene_threshold_ratio: float, scene_threshold_mean: float, local_threshold_ratio: float, max_local_ratio: float):
    diff = cv2.absdiff(curr_small, prev_small)
    mean_diff = float(diff.mean())
    _, mask = cv2.threshold(diff, 24, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)

    changed_pixels = int(cv2.countNonZero(mask))
    total_pixels = int(mask.shape[0] * mask.shape[1])
    changed_ratio = changed_pixels / total_pixels if total_pixels else 0.0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_bbox = None
    largest_area = 0
    if contours:
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area > largest_area:
                largest_area = area
                largest_bbox = (x, y, w, h)

    height, width = frame_shape[:2]
    hot_spot = None
    bbox_ratio = 0.0
    if largest_bbox:
        x, y, w, h = largest_bbox
        scale_x = width / mask.shape[1]
        scale_y = height / mask.shape[0]
        hot_spot = {
            "x": int((x + (w / 2)) * scale_x),
            "y": int((y + (h / 2)) * scale_y),
            "width": int(w * scale_x),
            "height": int(h * scale_y),
        }
        bbox_ratio = largest_area / total_pixels if total_pixels else 0.0

    event_type = None
    if changed_ratio >= scene_threshold_ratio or mean_diff >= scene_threshold_mean:
        event_type = "scene_change"
    elif changed_ratio >= local_threshold_ratio and bbox_ratio <= max_local_ratio:
        event_type = "local_ui_change"

    if event_type == "local_ui_change" and hot_spot:
        if hot_spot["width"] <= max(50, width * 0.14) and hot_spot["height"] <= max(50, height * 0.14):
            event_type = "possible_click_or_focus_change"

    return {
        "changed_ratio": round(changed_ratio, 5),
        "mean_diff": round(mean_diff, 3),
        "bbox_ratio": round(bbox_ratio, 5),
        "hot_spot": hot_spot,
        "event_type": event_type,
    }


def analyze_visual_timeline(video_path: Path, dense_dir: Path, events_dir: Path, sample_interval: float, jpeg_quality: int, scene_threshold_ratio: float, scene_threshold_mean: float, local_threshold_ratio: float, max_local_ratio: float):
    dense_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)
    for folder in (dense_dir, events_dir):
        for old_file in folder.glob("*.jpg"):
            old_file.unlink()

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    duration = total_frames / fps if fps else 0.0
    if duration <= 0:
        cap.release()
        return {"duration": 0, "dense_frames": [], "events": []}

    next_sample_sec = 0.0
    current_frame_index = 0
    prev_small = None
    dense_frames = []
    events = []
    sample_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        current_sec = current_frame_index / fps
        if current_sec + (1.0 / fps) < next_sample_sec:
            current_frame_index += 1
            continue

        sample_index += 1
        dense_name = f"frame_{sample_index:04d}_{current_sec:08.2f}s.jpg"
        dense_path = dense_dir / dense_name
        cv2.imwrite(str(dense_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])

        dense_frames.append(
            {
                "index": sample_index,
                "time": round(current_sec, 2),
                "path": str(dense_path),
            }
        )

        small = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(small, (320, 180), interpolation=cv2.INTER_AREA)

        if prev_small is not None:
            change = detect_change(
                prev_small,
                small,
                frame.shape,
                scene_threshold_ratio,
                scene_threshold_mean,
                local_threshold_ratio,
                max_local_ratio,
            )
            if change["event_type"]:
                event_name = f"event_{len(events) + 1:04d}_{current_sec:08.2f}s.jpg"
                event_path = events_dir / event_name
                cv2.imwrite(str(event_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
                events.append(
                    {
                        "index": len(events) + 1,
                        "time": round(current_sec, 2),
                        "frame_index": sample_index,
                        "event_type": change["event_type"],
                        "changed_ratio": change["changed_ratio"],
                        "mean_diff": change["mean_diff"],
                        "bbox_ratio": change["bbox_ratio"],
                        "hot_spot": change["hot_spot"],
                        "path": str(event_path),
                    }
                )

        prev_small = small
        next_sample_sec += sample_interval
        current_frame_index += 1

    cap.release()
    return {
        "duration": round(duration, 2),
        "fps": fps,
        "sample_interval": sample_interval,
        "dense_frames": dense_frames,
        "events": events,
    }


def write_visual_outputs(out_dir: Path, analysis: dict):
    json_path = out_dir / "visual-events.json"
    json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Visual timeline",
        "",
        f"- Duration: {analysis.get('duration')}s",
        f"- Sample interval: {analysis.get('sample_interval')}s",
        f"- Dense frames: {len(analysis.get('dense_frames', []))}",
        f"- Detected events: {len(analysis.get('events', []))}",
        "",
        "## Events",
        "",
    ]

    for event in analysis.get("events", []):
        line = f"- {event['time']:>7.2f}s | {event['event_type']} | diff={event['mean_diff']} | changed={event['changed_ratio']}"
        if event.get("hot_spot"):
            hot = event["hot_spot"]
            line += f" | hotspot=({hot['x']},{hot['y']}) size=({hot['width']}x{hot['height']})"
        line += f" | file=`events\\{Path(event['path']).name}`"
        lines.append(line)

    timeline_path = out_dir / "visual-timeline.md"
    timeline_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, timeline_path


def write_report(report_path: Path, url: str, info: dict, mp4_path: Path | None, vtt_path: Path | None, auto_txt: Path | None, asr_txt: Path | None, visual: dict):
    dense_count = len(visual.get("dense_frames", []))
    event_count = len(visual.get("events", []))
    lines = [
        "# Video processing report",
        "",
        f"- URL: {url}",
        f"- Video ID: {info.get('id')}",
        f"- Title: {info.get('title')}",
        f"- Channel: {info.get('channel')}",
        "",
        "## Artifacts",
        f"- Video downloaded: {'yes' if mp4_path else 'no'}",
        f"- Auto subtitles downloaded: {'yes' if vtt_path else 'no'}",
        f"- Auto transcript text generated: {'yes' if auto_txt and auto_txt.exists() else 'no'}",
        f"- Local ASR transcript generated: {'yes' if asr_txt and asr_txt.exists() else 'no'}",
        f"- Dense frames generated: {dense_count}",
        f"- Visual events detected: {event_count}",
        "",
    ]
    if mp4_path:
        lines.append(f"- MP4: `{mp4_path.name}`")
    if vtt_path:
        lines.append(f"- VTT: `{vtt_path.name}`")
    if auto_txt and auto_txt.exists():
        lines.append(f"- Auto transcript: `{auto_txt.name}`")
    if asr_txt and asr_txt.exists():
        lines.append(f"- ASR transcript: `{asr_txt.name}`")
    lines.append("- Visual timeline: `visual-timeline.md`")
    lines.append("- Visual event data: `visual-events.json`")
    lines.append("")
    lines.append("## Visual understanding")
    lines.append("- Dense sampling captured the video every 0.5 seconds by default.")
    lines.append("- Full-screen changes are classified as `scene_change`.")
    lines.append("- Smaller localized changes are classified as `local_ui_change` or `possible_click_or_focus_change`.")
    lines.append("- Hotspot coordinates are heuristic estimates based on changed regions between sampled frames.")
    lines.append("")
    if visual.get("events"):
        lines.append("## First detected events")
        for event in visual["events"][:12]:
            summary = f"- {event['time']:>7.2f}s | {event['event_type']} | diff={event['mean_diff']} | changed={event['changed_ratio']}"
            if event.get("hot_spot"):
                hot = event["hot_spot"]
                summary += f" | hotspot=({hot['x']},{hot['y']})"
            lines.append(summary)
        lines.append("")
    lines.append("## Cleanup note")
    lines.append("- After using the artifacts, ask whether the user wants to delete the downloaded video and generated outputs.")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    if args.cleanup_video_id:
        cleanup_video_folder(output_root, args.cleanup_video_id)
        return

    if not args.url:
        raise SystemExit("--url is required unless --cleanup-video-id is used")

    info, out_dir, mp4_path, vtt_path = download_assets(args.url, output_root, args.language)
    if not mp4_path:
        raise RuntimeError("Failed to download the MP4 file.")

    auto_txt = None
    if vtt_path:
        auto_txt = out_dir / "transcript.auto.txt"
        vtt_to_text(vtt_path, auto_txt)

    asr_txt = out_dir / "transcript.asr.txt"
    asr_segments = out_dir / "transcript.asr.segments.json"
    transcribe_with_whisper(mp4_path, asr_txt, asr_segments, args.model, args.language)

    visual = analyze_visual_timeline(
        mp4_path,
        out_dir / "frames-dense",
        out_dir / "frames-events",
        args.sample_interval,
        args.dense_frame_quality,
        args.scene_threshold_ratio,
        args.scene_threshold_mean,
        args.local_threshold_ratio,
        args.max_local_ratio,
    )
    write_visual_outputs(out_dir, visual)

    report_path = out_dir / "report.md"
    write_report(report_path, args.url, info, mp4_path, vtt_path, auto_txt, asr_txt, visual)

    print(str(report_path))


if __name__ == "__main__":
    main()
