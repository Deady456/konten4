"""
Quick test: Pollination images + voice + watermark. No music.
"""
import subprocess
import urllib.request
import urllib.parse
import time
from pathlib import Path
from . import voice, captions, assemble, state, branding

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "output" / "test_pollination"
WORK.mkdir(parents=True, exist_ok=True)


def download_pollination(prompt: str, out_path: Path, width=1080, height=1920) -> Path:
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&seed={int(time.time())}"
    print(f"    pollination: {prompt[:40]}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        out_path.write_bytes(resp.read())
    print(f"    downloaded: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
    return out_path


def run():
    t0 = time.time()

    # 1. Generate voice
    print("\n=== 1/5 Generating voice ===")
    text = (
        "Taukah kamu? Otak manusia hanya beratnya satu setengah kilogram, "
        "tapi mampu memproses informasi setara komputer super. "
        "Setiap detik, otakmu melakukan triliunan operasi. "
        "Itu lebih cepat dari superkomputer manapun di dunia."
    )
    voice_path = WORK / "voice.mp3"
    voice.synth(text, voice_path)
    print(f"    voice: {voice_path.stat().st_size // 1024} KB")

    # 2. Get voice duration
    print("\n=== 2/5 Getting duration ===")
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(voice_path)]
    dur = float(subprocess.check_output(cmd).decode().strip())
    print(f"    duration: {dur:.1f}s")

    # 3. Download Pollination images (no audio)
    print("\n=== 3/5 Downloading Pollination images ===")
    prompts = [
        "human brain anatomy diagram, scientific illustration, dark background",
        "neural network synapses glowing, abstract science art, blue tones",
        "supercomputer server room, futuristic technology, cinematic lighting",
    ]
    scene_dur = dur / len(prompts)
    images = []
    for i, p in enumerate(prompts):
        img = WORK / f"scene_{i}.png"
        download_pollination(p, img)
        images.append(img)

    # 4. Create video from images + voice
    print("\n=== 4/5 Assembling video ===")
    # Build ffmpeg inputs
    cmd = ["ffmpeg", "-y"]
    for img in images:
        cmd += ["-loop", "1", "-t", f"{scene_dur:.2f}", "-i", str(img)]
    cmd += ["-i", str(voice_path)]

    n = len(images)
    filter_parts = []
    for i in range(n):
        filter_parts.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30,setsar=1[v{i}]")

    if n > 1:
        concat_inputs = "".join(f"[v{i}]" for i in range(n))
        filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vout]")
    else:
        filter_parts.append(f"[v0]null[vout]")

    filter_complex = ";".join(filter_parts)
    raw_video = WORK / "raw.mp4"
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", f"{n}:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(raw_video),
    ]

    print(f"    rendering {n} scenes...")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"    FAILED: {p.stderr[-300:]}")
        return
    print(f"    raw: {raw_video.stat().st_size // (1024*1024)} MB")

    # 5. Apply watermark
    print("\n=== 5/5 Applying watermark ===")
    final = WORK / "final.mp4"
    if final.exists():
        final.unlink()
    branded = branding.apply_all(raw_video, WORK)
    if branded != raw_video:
        branded.rename(final)
    else:
        raw_video.rename(final)

    elapsed = time.time() - t0
    print(f"\n{'='*50}")
    print(f"DONE in {elapsed:.0f}s")
    print(f"Video: {final}")
    print(f"Size: {final.stat().st_size // (1024*1024)} MB")


if __name__ == "__main__":
    run()
