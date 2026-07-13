from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build as gbuild
from googleapiclient.http import MediaFileUpload
from .config import ROOT, CONFIG

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
CLIENT_SECRET = ROOT / "client_secret.json"


def _token_path() -> Path:
    """Return token file path based on channel config."""
    channel = CONFIG.get("upload", {}).get("channel", "default")
    return ROOT / f"token_{channel}.json"


def get_service():
    token_path = _token_path()
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.scopes = None  # pakai granted scope asli saat refresh (hindari invalid_scope)
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return gbuild("youtube", "v3", credentials=creds)


def _apply_ai_disclosure(description: str) -> str:
    """Add AI disclosure to description if enabled."""
    cfg = CONFIG.get("ai_disclosure", {})
    if not cfg.get("enabled", False):
        return description

    disclosure_text = cfg.get("text", "Konten ini dibuat dengan bantuan AI.")
    position = cfg.get("position", "description_only")

    # Check if disclosure already present
    if disclosure_text.lower() in description.lower():
        return description

    # Add disclosure at the end
    disclosure_block = f"\n\n{'='*40}\n{disclosure_text}\n{'='*40}"
    return description + disclosure_block


def upload_video(video_path: Path, title: str, description: str, tags: list[str],
                 publish_at: str | None = None) -> str:
    yt = get_service()
    up = CONFIG["upload"]
    all_tags = list({*tags, *up["default_tags"]})

    # Apply AI disclosure to description
    description = _apply_ai_disclosure(description)

    status = {"selfDeclaredMadeForKids": up["made_for_kids"]}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    else:
        status["privacyStatus"] = up["privacy"]

    body = {
        "snippet": {
            "title": title[:95],
            "description": description,
            "tags": all_tags,
            "categoryId": up["category_id"],
        },
        "status": status,
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]