"""Bước 6: upload lên YouTube qua YouTube Data API v3 (mặc định private)."""
import json
from pathlib import Path
from .config import ROOT

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token, secret = ROOT / "token.json", ROOT / "client_secret.json"
    creds = Credentials.from_authorized_user_file(token, SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secret.exists():
                raise FileNotFoundError("Thiếu client_secret.json — xem README mục 'Kết nối YouTube'.")
            creds = InstalledAppFlow.from_client_secrets_file(secret, SCOPES).run_local_server(port=0)
        token.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(cfg: dict, video_dir: Path) -> str:
    from googleapiclient.http import MediaFileUpload

    story = json.loads((video_dir / "story.json").read_text(encoding="utf-8"))
    yt, uc = story["youtube"], cfg["upload"]
    body = {
        "snippet": {"title": yt["title"][:100], "description": yt["description"],
                    "tags": yt.get("tags", [])[:15], "categoryId": uc["category_id"]},
        "status": {"privacyStatus": uc["privacy"], "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": uc.get("contains_synthetic_media", True)},
    }
    req = _service().videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(video_dir / "final.mp4"), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]
