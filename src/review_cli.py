"""
Review CLI - Manage video drafts for review.

Usage:
    python -m src.review --list              # List pending drafts
    python -m src.review --approve <name>    # Approve a draft
    python -m src.review --reject <name>     # Reject a draft
"""
import argparse
import json
import shutil
from . import review


def list_drafts():
    """List all pending drafts."""
    drafts = review.list_drafts(status="pending")

    if not drafts:
        print("\n  Tidak ada draft yang menunggu review.\n")
        return

    print(f"\n  Drafts menunggu review ({len(drafts)}):\n")
    for i, d in enumerate(drafts, 1):
        print(f"  {i}. {d['name']}")
        print(f"     Topic: {d['topic']}")
        print(f"     Title: {d['title']}")
        print(f"     Created: {d['created_at']}")
        print()

    print("  Untuk approve: python -m src.review --approve <nama-draft>")
    print("  Untuk reject: python -m src.review --reject <nama-draft>\n")


def approve_draft(name: str):
    """Approve a draft and prepare for upload."""
    meta = review.approve_draft(name)
    if meta is None:
        print(f"  Draft '{name}' tidak ditemukan.")
        return

    print(f"\n  Draft approved: {name}")
    print(f"  Title: {meta.get('title')}")
    print(f"  Video: {meta.get('video_path')}")
    print(f"\n  Untuk upload, jalankan:")
    print(f"  python -m src.upload_draft {name}\n")


def reject_draft(name: str, reason: str = ""):
    """Reject a draft."""
    success = review.reject_draft(name, reason)
    if success:
        print(f"  Draft '{name}' ditolak.")
    else:
        print(f"  Draft '{name}' tidak ditemukan.")


def main():
    p = argparse.ArgumentParser(description="Review Manager")
    p.add_argument("--list", action="store_true", help="List pending drafts")
    p.add_argument("--approve", metavar="NAME", help="Approve a draft")
    p.add_argument("--reject", metavar="NAME", help="Reject a draft")
    p.add_argument("--reason", default="", help="Reason for rejection")

    args = p.parse_args()

    if args.list:
        list_drafts()
    elif args.approve:
        approve_draft(args.approve)
    elif args.reject:
        reject_draft(args.reject, args.reason)
    else:
        list_drafts()


if __name__ == "__main__":
    main()
