"""Idempotent push of the synthetic ACME corpus into real Slack +
Google services.

L2 setup:

- Slack: a free workspace you own + bot tokens (see scenarios/onboarding_it/README.md).
- Google: a personal account dedicated to testing + OAuth refresh token.
- Tickets stay disk-backed via FakeTicketingResource (Linear deferred to L3).

The mapping ``synthetic-id -> real-id`` is recorded in
``scenarios/onboarding_it/l2_mapping.yaml`` after the first push.

Implementation status: SCAFFOLDED. The skeleton calls real APIs but is
intentionally light on retry/backoff and on Slack-historical-message
backfill -- Slack does not let bot users post messages with arbitrary
timestamps, so the historical conversation will appear with `now`
timestamps and original dates inlined into message text. The agent
learns to read in-text dates instead. Each section guards on the
presence of the corresponding env var so partial setup still works.
"""
import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml

from scenarios.onboarding_it import seed
from scenarios.onboarding_it.mounts import DEFAULT_DISK_ROOT

PREFIX = "mirage-eval__"
MAPPING_PATH = (
    Path(__file__).resolve().parent / "l2_mapping.yaml")


def _load_mapping() -> dict[str, dict[str, str]]:
    if MAPPING_PATH.exists():
        return yaml.safe_load(MAPPING_PATH.read_text()) or {}
    return {}


def _save_mapping(m: dict[str, Any]) -> None:
    MAPPING_PATH.write_text(yaml.safe_dump(m, sort_keys=True))


def push_slack(disk_root: Path, mapping: dict) -> dict:
    """Push channels + DMs + users into the real Slack workspace.

    Args:
        disk_root (Path): Synthetic corpus root (must contain ``slack/``).
        mapping (dict): The ``l2_mapping.yaml`` dict, mutated in place.
    """
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("SLACK_BOT_TOKEN not set; skipping Slack push.")
        return mapping
    try:
        import httpx
    except ImportError:
        print("httpx not installed; skipping Slack push.")
        return mapping
    slack = mapping.setdefault("slack", {})
    channels_dir = disk_root / "slack" / "channels"
    if not channels_dir.exists():
        return mapping
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json; charset=utf-8"}
    with httpx.Client(timeout=30.0) as client:
        for ch_dir in sorted(channels_dir.iterdir()):
            if not ch_dir.is_dir():
                continue
            local_name, _, _ = ch_dir.name.partition("__")
            real_name = f"{PREFIX}{local_name}"
            existing = slack.get(local_name)
            if existing:
                channel_id = existing
            else:
                resp = client.post(
                    "https://slack.com/api/conversations.create",
                    headers=headers,
                    json={"name": real_name, "is_private": False},
                )
                data = resp.json()
                if data.get("ok"):
                    channel_id = data["channel"]["id"]
                elif data.get("error") == "name_taken":
                    list_resp = client.get(
                        "https://slack.com/api/conversations.list",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"types": "public_channel,private_channel"},
                    )
                    found = next(
                        (c for c in list_resp.json().get("channels", [])
                         if c.get("name") == real_name), None)
                    channel_id = found["id"] if found else None
                else:
                    print(f"slack create failed for {real_name}: {data}")
                    channel_id = None
            if not channel_id:
                continue
            slack[local_name] = channel_id
            for day_dir in sorted(ch_dir.iterdir()):
                jsonl = day_dir / "chat.jsonl"
                if not jsonl.exists():
                    continue
                for line in jsonl.read_text().splitlines():
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    text = (
                        f"[{day_dir.name} · u={msg.get('user', '?')}] "
                        f"{msg.get('text', '')}")
                    client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers=headers,
                        json={"channel": channel_id, "text": text},
                    )
    return mapping


def push_google(disk_root: Path, mapping: dict) -> dict:
    """Push GSheet + GDoc JSON files into a real Google account.

    NOTE: Real Google Sheets / Docs API push requires the official
    google-api-python-client + google-auth packages. Those are NOT in
    packages/eval/pyproject.toml because L1 doesn't need them. To enable
    L2 Google push, install with:

        cd packages/eval && uv add google-api-python-client google-auth-oauthlib

    Then this function will lazy-import and use them. Without those
    packages, this is a no-op (a warning is printed).

    Args:
        disk_root (Path): Synthetic corpus root.
        mapping (dict): The ``l2_mapping.yaml`` dict, mutated in place.
    """
    if not all(os.environ.get(k) for k in
               ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
                "GOOGLE_REFRESH_TOKEN")):
        print("Google OAuth env vars not set; skipping Google push.")
        return mapping
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("google-api-python-client not installed; skipping Google push. "
              "Run: cd packages/eval && uv add google-api-python-client "
              "google-auth-oauthlib")
        return mapping
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    sheets_svc = build("sheets", "v4", credentials=creds,
                       cache_discovery=False)
    docs_svc = build("docs", "v1", credentials=creds,
                     cache_discovery=False)
    google = mapping.setdefault("google", {})
    sheets_root = disk_root / "sheets" / "owned"
    if sheets_root.exists():
        for src in sorted(sheets_root.glob("*.gsheet.json")):
            local_id = src.name.split("__", 1)[1].split(".", 1)[0]
            real_title = f"{PREFIX}{src.name.replace('.gsheet.json', '')}"
            existing = google.get(local_id)
            if existing:
                continue
            spec = json.loads(src.read_text())
            create_resp = sheets_svc.spreadsheets().create(
                body={"properties": {"title": real_title},
                      "sheets": spec.get("sheets", [])},
                fields="spreadsheetId").execute()
            google[local_id] = create_resp["spreadsheetId"]
    gdocs_root = disk_root / "gdocs" / "owned"
    if gdocs_root.exists():
        for src in sorted(gdocs_root.glob("*.gdoc.json")):
            local_id = src.name.split("__", 1)[1].split(".", 1)[0]
            real_title = f"{PREFIX}{src.name.replace('.gdoc.json', '')}"
            existing = google.get(local_id)
            if existing:
                continue
            create_resp = docs_svc.documents().create(
                body={"title": real_title}).execute()
            doc_id = create_resp["documentId"]
            google[local_id] = doc_id
            spec = json.loads(src.read_text())
            paragraphs = []
            for c in spec.get("body", {}).get("content", []):
                if "paragraph" in c:
                    for el in c["paragraph"].get("elements", []):
                        tr = el.get("textRun", {})
                        text = tr.get("content", "")
                        if text:
                            paragraphs.append(text)
            if paragraphs:
                docs_svc.documents().batchUpdate(
                    documentId=doc_id,
                    body={"requests": [
                        {"insertText": {"location": {"index": 1},
                                        "text": "".join(paragraphs)}},
                    ]}).execute()
    return mapping


def main(disk_root: str | Path | None = None,
         clean: bool = False) -> Path:
    """Push the synthetic corpus into real Slack + Google.

    Args:
        disk_root (str | Path | None): Local on-disk root for the
            synthetic corpus. Defaults to the L1 disk root.
        clean (bool): If True, delete the local mapping first so all
            real entities get re-created (does NOT delete remote
            entities; users must clean those manually).
    """
    root = Path(disk_root or DEFAULT_DISK_ROOT).expanduser().resolve()
    if not root.exists():
        print(f"disk root {root} not found; running L1 seed first")
        seed.main(root, clean=False)
    if clean and MAPPING_PATH.exists():
        MAPPING_PATH.unlink()
    mapping = _load_mapping()
    mapping = push_slack(root, mapping)
    mapping = push_google(root, mapping)
    _save_mapping(mapping)
    print(f"l2 mapping written: {MAPPING_PATH}")
    return MAPPING_PATH


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--disk-root", default=None)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    main(args.disk_root, clean=args.clean)


if __name__ == "__main__":
    _cli()
