import os
import re
import json
import time
import random
import requests
import subprocess
from pathlib import Path
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from .config import CONFIG, ROOT

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

def probe_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            check=True, capture_output=True, text=True,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 60.0


def _search_wikimedia_mystery(query: str) -> list[str]:
    """Fetch Asian mythology and ancient archaeology photos from Wikimedia."""
    url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={quote(query)}&gsrlimit=6&prop=pageimages&piprop=original|thumbnail&pithumbsize=1080"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            urls = []
            for pid, page in pages.items():
                img = page.get("original", {}).get("source") or page.get("thumbnail", {}).get("source")
                if img and "logo" not in img.lower() and "icon" not in img.lower():
                    urls.append(img)
            return urls
    except Exception:
        pass
    return []


def _generate_pollinations_flux_horror(prompt: str, out_path: Path, seed: int = None) -> bool:
    """Generate dark, eerie, atmospheric Asian horror/mystery imagery using Pollinations FLUX.1."""
    try:
        clean_p = re.sub(r'[^a-zA-Z0-9\s,.-]', '', prompt).strip()
        enhanced_prompt = f"{clean_p}, asian horror folklore, dark eerie atmosphere, heavy volumetric mist, cinematic horror movie still, mysterious shadows, 8k photorealistic, chilling, masterpiece"
        seed_param = f"&seed={seed}" if seed else f"&seed={random.randint(1, 999999)}"
        url = f"https://image.pollinations.ai/prompt/{quote(enhanced_prompt)}?width=1080&height=1920&model=flux&nologo=true{seed_param}"
        
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code == 200 and len(r.content) > 5000:
            out_path.write_bytes(r.content)
            with Image.open(out_path) as im:
                im.verify()
            return True
    except Exception:
        pass
    return False


def _download_image(url: str, out_path: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        if r.status_code == 200 and len(r.content) > 3000:
            out_path.write_bytes(r.content)
            with Image.open(out_path) as im:
                im.verify()
            return True
    except Exception:
        pass
    return False


def _process_image_card(
    base_img_path: Path,
    out_path: Path,
    topic_label: str = "MISTERI ASIA",
    w: int = 1080,
    h: int = 1920,
    is_hook: bool = False
):
    try:
        im = Image.open(base_img_path).convert("RGBA")
    except Exception:
        im = Image.new("RGBA", (w, h), (15, 10, 15, 255))

    iw, ih = im.size
    target_ratio = w / h
    img_ratio = iw / ih

    if img_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        offset = (iw - new_w) // 2
        im = im.crop((offset, 0, offset + new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        offset = (ih - new_h) // 2
        im = im.crop((0, offset, iw, offset + new_h))

    im = im.resize((w, h), Image.Resampling.LANCZOS)

    # Dark atmospheric horror grading
    contrast = ImageEnhance.Contrast(im)
    im = contrast.enhance(1.18)
    color = ImageEnhance.Color(im)
    im = color.enhance(0.9)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Deep dark vignette
    for y in range(400):
        alpha = int(220 * (1.0 - y / 400.0) ** 1.5)
        draw.line([(0, y), (w, y)], fill=(5, 5, 10, alpha))
    for y in range(h - 500, h):
        factor = (y - (h - 500)) / 500.0
        alpha = int(230 * (factor ** 1.3))
        draw.line([(0, y), (w, y)], fill=(5, 5, 10, alpha))

    if is_hook:
        badge_y = 120
        draw.rectangle([(50, badge_y), (360, badge_y + 60)], fill=(160, 20, 20, 230))
        font = ImageFont.load_default()
        draw.text((70, badge_y + 20), topic_label.upper(), fill=(255, 255, 255, 255))

    final_img = Image.alpha_composite(im, overlay).convert("RGB")
    final_img.save(out_path, quality=95)
    return out_path


def _image_to_video(img_path: Path, out_path: Path, duration: float, w: int, h: int, fps: int, zoom_direction: int = 0):
    frames = int(duration * fps)
    
    if zoom_direction % 2 == 0:
        zoom_expr = f"zoompan=z='min(1.18,1.0+0.007*on)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
    else:
        zoom_expr = f"zoompan=z='max(1.0,1.15-0.007*on)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
        "-vf",
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"{zoom_expr}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.3f}",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True)


def _fallback_video(out_path: Path, duration: float, w: int, h: int, fps: int):
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=#0f0a14:s={w}x{h}:r={fps}:d={duration:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True)


def _calculate_scene_durations(words: list[dict], scenes: list[dict], total_audio_dur: float) -> list[float]:
    if not words or not scenes:
        per_scene = total_audio_dur / max(1, len(scenes))
        return [max(3.0, per_scene) for _ in scenes]

    spoken = [s.get("text", "").lower() for s in scenes]
    durations = []
    cursor = 0
    for i, sentence in enumerate(spoken):
        scene_words = [w.strip(".,!?;:\"'") for w in sentence.split()]
        start_idx = cursor
        end_idx = min(cursor + len(scene_words), len(words))
        if i == len(spoken) - 1:
            end_idx = len(words)
        start_t = words[start_idx]["start"] if start_idx < len(words) else words[-1]["end"]
        end_t = words[end_idx - 1]["end"] if end_idx > 0 else start_t
        durations.append(max(2.5, end_t - start_t))
        cursor = end_idx

    tot = sum(durations)
    if tot < total_audio_dur:
        extra = total_audio_dur - tot + 0.5
        durations[-1] += extra
    return durations


def fetch_all(scenes: list[dict], out_dir: Path, words: list[dict] = None, voice_audio: Path = None) -> list[Path]:
    """
    Generate dark Asian mystery visuals (Pollinations FLUX.1 Horror + Wikimedia Asian Archaeology)
    and generate dynamic 2.5-3.5s multi-cut clips covering full audio duration.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    all_clips = []
    v = CONFIG["video"]
    w, h, fps = v["width"], v["height"], v["fps"]

    total_audio_dur = probe_duration(voice_audio) if (voice_audio and voice_audio.exists()) else (len(scenes) * 7.0)
    scene_durations = _calculate_scene_durations(words, scenes, total_audio_dur)

    clip_counter = 0

    print(f"    [Mystery Visuals] Generating horror/mystery cuts for {len(scenes)} scenes ({total_audio_dur:.1f}s audio)...")

    for i, scene in enumerate(scenes):
        total_scene_dur = scene_durations[i]
        num_subclips = max(1, int(round(total_scene_dur / 3.0)))
        subclip_dur = total_scene_dur / num_subclips

        queries = []
        factual = scene.get("factual_subject")
        if factual and isinstance(factual, str) and factual.lower() != "null":
            queries.append(factual.strip())

        vq = scene.get("visual_query", "")
        if vq:
            queries.append(vq.strip())

        for sub_idx in range(num_subclips):
            out_clip_path = out_dir / f"clip_{clip_counter:03d}.mp4"
            raw_img_path = out_dir / f"raw_{clip_counter:03d}.jpg"
            final_img_path = out_dir / f"card_{clip_counter:03d}.jpg"

            prompt = queries[sub_idx % len(queries)] if queries else scene.get("text", "ancient asian mystery folklore")
            img_ready = _generate_pollinations_flux_horror(prompt, raw_img_path, seed=clip_counter + 300)

            if not img_ready:
                # Fallback to Wikimedia
                wiki_urls = _search_wikimedia_mystery(prompt)
                for u in wiki_urls:
                    if _download_image(u, raw_img_path):
                        img_ready = True
                        break

            if img_ready:
                _process_image_card(
                    base_img_path=raw_img_path,
                    out_path=final_img_path,
                    topic_label="MISTERI ASIA",
                    w=w, h=h,
                    is_hook=(i == 0 and sub_idx == 0)
                )
                _image_to_video(final_img_path, out_clip_path, subclip_dur, w, h, fps, zoom_direction=clip_counter)
            else:
                _fallback_video(out_clip_path, subclip_dur, w, h, fps)

            all_clips.append(out_clip_path)
            clip_counter += 1

        print(f"    scene {i+1}/{len(scenes)}: {total_scene_dur:.1f}s -> {num_subclips} mystery cuts generated")

    print(f"    [Mystery Visuals] Ready: {len(all_clips)} dynamic clips covering full video duration.")
    return all_clips
