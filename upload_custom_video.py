import sys
from pathlib import Path
from src.upload import upload_video

video_path = Path("output/KONTEN_MISTERI_NEVADA_BODYCAM_FINAL.mp4")
title = "Rekaman Bodycam Polisi di Jalan Gurun Jam 2 Pagi! Sosok Apa Ini?! #shorts"
desc = """Rekaman found footage bodycam patroli malam hari di jalan gurun yang menangkap bayangan misterius melesat di balik bebatuan.

Apa menurut kalian sosok tersebut? Tulis di komentar!

#shorts #misteri #foundfootage #bodycam #kisahmisteri #horor #unexplained
"""
tags = ["shorts", "misteri", "found footage", "bodycam", "kisah misteri", "horor", "penampakan", "unexplained"]

print(f"Mengupload video: {video_path}...")
video_id = upload_video(
    video_path=video_path,
    title=title,
    description=desc,
    tags=tags
)

print(f"UPLOAD BERHASIL! Video ID: {video_id}")
print(f"URL: https://youtube.com/shorts/{video_id}")
