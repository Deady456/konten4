import argparse
import re
import time
from datetime import datetime
from . import script, voice, captions, visuals, assemble, upload, state
from . import music, branding, review
from .config import CONFIG, OUTPUT_DIR


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "short"


def _log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def run_once(publish_at: str | None = None, upload_to_youtube: bool = True,
             force_review: bool = False) -> dict:
    """
    Run the full pipeline.

    Args:
        publish_at: ISO8601 UTC timestamp for scheduled publish
        upload_to_youtube: Whether to upload to YouTube
        force_review: Force save as draft regardless of mode
    """
    # ============================================================
    # Step 0: Determine format variation
    # ============================================================
    content_cfg = CONFIG.get("content_variation", {})
    if content_cfg.get("enabled", False):
        formats = content_cfg.get("formats", ["list"])
        s = state.load()
        format_idx = s.get("_format_idx", 0)
        selected_format = formats[format_idx % len(formats)]
        state.update({"_format_idx": format_idx + 1})
        _log(f"0/7 Content format: {selected_format}")
    else:
        selected_format = None

    # ============================================================
    # Step 1: Generate script
    # ============================================================
    _log("1/9 Generating script with LLM")
    data = script.generate(content_format=selected_format)
    _log(f"    topic: {data['topic']} ({len(data['scenes'])} scenes)")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work = OUTPUT_DIR / f"{stamp}_{slug(data['topic'])}"
    work.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # Step 2: Synthesize voiceover (with variety)
    # ============================================================
    _log("2/9 Synthesizing voiceover")
    voice_mp3 = voice.synth(data["full_text"], work / "voice.mp3")
    _log(f"    voice saved ({voice_mp3.stat().st_size/1024:.0f} KB)")

    # ============================================================
    # Step 3: Transcribe for captions
    # ============================================================
    _log("3/9 Transcribing for word-level captions (Faster-Whisper)")
    _log("    loading model (first run downloads)...")
    t0 = time.time()
    words = captions.transcribe_words(voice_mp3, original_text=data["full_text"])
    _log(f"    {len(words)} words in {time.time()-t0:.1f}s")

    # ============================================================
    # Step 4: Fetch B-roll footage
    # ============================================================
    _log("4/9 Fetching footage from Pexels")
    scene_videos = visuals.fetch_for_scenes(data["scenes"], work / "broll")
    _log(f"    {len(scene_videos)} clips ready")

    # ============================================================
    # Step 5: Write caption file
    # ============================================================
    _log("5/9 Writing caption file")
    from .config import CONFIG as CFG
    ass_path = captions.write_ass(words, work / "captions.ass",
                                  CFG["video"]["width"], CFG["video"]["height"])

    # ============================================================
    # Step 6: Mix background music
    # ============================================================
    _log("6/9 Mixing background music")
    # Get audio duration first
    from .assemble import probe_duration
    audio_dur = probe_duration(voice_mp3)

    mixed_audio = work / "voice_mixed.aac"
    music.mix_with_voice(voice_mp3, mixed_audio, audio_dur, data["scenes"])

    # ============================================================
    # Step 7: Assemble video
    # ============================================================
    _log("7/9 Assembling final video with ffmpeg")
    _log("    processing scenes (scale/crop/loop)...")
    t0 = time.time()
    final = assemble.build(
        scene_videos=scene_videos,
        voice_audio=mixed_audio,  # Use mixed audio instead of raw voice
        captions_ass=ass_path,
        words=words,
        scenes=data["scenes"],
        out_path=work / "final_raw.mp4",
        work_dir=work / "ffmpeg",
        videos_per_scene=2,
    )
    dur = time.time() - t0
    sz = final.stat().st_size / (1024 * 1024)
    _log(f"    raw video: {final.name} ({sz:.0f} MB, {dur:.0f}s render)")

    # ============================================================
    # Step 8: Apply branding (intro/outro/watermark)
    # ============================================================
    _log("8/9 Applying branding")
    branded = branding.apply_all(final, work / "branding")
    if branded != final:
        # Move branded to final
        final_branded = work / "final.mp4"
        branded.rename(final_branded)
        final = final_branded
    else:
        # Just rename raw to final
        final_branded = work / "final.mp4"
        final.rename(final_branded)
        final = final_branded

    sz = final.stat().st_size / (1024 * 1024)
    _log(f"    final: {final.name} ({sz:.0f} MB)")

    # ============================================================
    # Step 9: Review or Upload
    # ============================================================
    video_id = None

    # Check if review is needed
    s = state.load()
    video_count = len(s.get("published", []))
    needs_review = force_review or review.should_review(video_count)

    if needs_review and upload_to_youtube:
        _log("9/9 Saving draft for review")
        draft_path = review.save_draft(data, final)
        _log(f"    Draft saved: {draft_path.name}")
        _log("    Run: python -m src.review --list  (to see drafts)")
        _log("    Run: python -m src.review --approve <name>  (to approve)")
    elif upload_to_youtube:
        _log("9/9 Uploading to YouTube")
        video_id = upload.upload_video(
            video_path=final,
            title=data["title"],
            description=data["description"],
            tags=data["tags"],
            publish_at=publish_at,
        )
        _log(f"    uploaded: https://youtube.com/shorts/{video_id}")
    else:
        _log("9/9 Upload skipped (--no-upload)")

    # Save state
    state.add_topic(data["topic"])
    state.add_published({
        "ts": stamp,
        "topic": data["topic"],
        "title": data["title"],
        "path": str(final),
        "video_id": video_id,
        "publish_at": publish_at,
        "format": selected_format,
        "voice": data.get("_voice_name", "unknown"),
    })

    return {"video_id": video_id, "path": str(final), "topic": data["topic"]}


def main():
    p = argparse.ArgumentParser(description="FreeFaceless Pipeline")
    p.add_argument("--no-upload", action="store_true", help="Build only, don't upload")
    p.add_argument("--publish-at", default=None,
                   help="ISO8601 UTC timestamp for scheduled publish")
    p.add_argument("--force-review", action="store_true",
                   help="Force save as draft for review")
    args = p.parse_args()

    run_once(
        publish_at=args.publish_at,
        upload_to_youtube=not args.no_upload,
        force_review=args.force_review,
    )

    print("\n" + "-" * 60)
    print("Done!")
    print("-" * 60)


if __name__ == "__main__":
    main()
