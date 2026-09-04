import sys
from pathlib import Path
from src.upload import upload_video

video_path = Path("output/KONTEN_MISTERI_FOREST_BODYCAM_FINAL.mp4")
title = "Rekaman Bodycam Polisi Kehutanan di Hutan Kabut Jam 3 Pagi! Sosok Apa Ini?! #shorts"
desc = """Rekaman found footage bodycam patroli polisi kehutanan menembus kabut tebal hutan pinus malam hari. Di detik ke-3 tampak bayangan misterius berdiri di antara pepohonan.

Menurut kalian sosok apa itu? Tulis di kolom komentar!

#shorts #misteri #bodycam #foundfootage #kisahmisteri #horor #hutanangker #penampakan #unexplained
"""
tags = ["shorts", "misteri", "bodycam", "found footage", "kisah misteri", "horor", "hutan angker", "penampakan", "unexplained"]

print(f"Mengupload video: {video_path}...")
video_id = upload_video(
    video_path=video_path,
    title=title,
    description=desc,
    tags=tags
)

print(f"UPLOAD BERHASIL! Video ID: {video_id}")
print(f"URL: https://youtube.com/shorts/{video_id}")
