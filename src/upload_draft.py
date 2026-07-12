"""
Upload approved drafts to YouTube.

Usage:
    python -m src.upload_draft <draft-name>    # Upload specific draft
    python -m src.upload_draft --all           # Upload all approved drafts
"""
import argparse
import json
from pathlib import Path
from . import review, upload
from .config import ROOT


def upload_draft(draft_name: str) -> bool:
    """Upload a single approved draft."""
    draft_dir = ROOT / "drafts" / draft_name
    meta_path = draft_dir / "draft.json"
    video_path = draft_dir / "final.mp4"

    if not meta_path.exists():
        print(f"  Draft '{draft_name}' tidak ditemukan.")
        return False

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if meta.get("status") != "approved":
        print(f"  Draft '{draft_name}' belum di-approve.")
        return False

    if not video_path.exists():
        print(f"  Video tidak ditemukan: {video_path}")
        return False

    print(f"\n  Uploading: {draft_name}")
    print(f"  Title: {meta.get('title')}")

    video_id = upload.upload_video(
        video_path=video_path,
        title=meta.get("title", ""),
        description=meta.get("description", ""),
        tags=meta.get("tags", []),
    )

    print(f"  Uploaded: https://youtube.com/shorts/{video_id}")

    # Mark as uploaded
    meta["status"] = "uploaded"
    meta["video_id"] = video_id
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return True


def upload_all_approved():
    """Upload all approved drafts."""
    drafts = review.list_drafts(status="approved")

    if not drafts:
        print("\n  Tidak ada draft yang di-approve.\n")
        return

    print(f"\n  Uploading {len(drafts)} draft(s)...\n")

    success = 0
    for d in drafts:
        if upload_draft(d["name"]):
            success += 1

    print(f"\n  Selesai: {success}/{len(drafts)} uploaded.\n")


def main():
    p = argparse.ArgumentParser(description="Upload Draft Manager")
    p.add_argument("draft", nargs="?", help="Draft name to upload")
    p.add_argument("--all", action="store_true", help="Upload all approved drafts")

    args = p.parse_args()

    if args.all:
        upload_all_approved()
    elif args.draft:
        upload_draft(args.draft)
    else:
        print("  Usage: python -m src.upload_draft <draft-name>")
        print("  Or: python -m src.upload_draft --all\n")


if __name__ == "__main__":
    main()
