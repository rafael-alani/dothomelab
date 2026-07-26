#!/usr/bin/env python3
"""Exercise PinePods through its supported web and GPodder APIs.

The test uses only the public PinePods news feed, never prints credentials or
response bodies, and writes a sanitized evidence summary to canonical appdata.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    data: Any | None = None,
    api_key: str | None = None,
    basic: tuple[str, str] | None = None,
) -> tuple[Any, bytes]:
    body = None
    headers = {"Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["Api-Key"] = api_key
    if basic:
        token = base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    req = urllib.request.Request(
        urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"{method} {path} failed with HTTP {error.code}"
        ) from None
    if content_type == "application/json":
        return json.loads(raw), raw
    return raw.decode(), raw


def wait_until(description: str, deadline_seconds: int, probe: Any) -> Any:
    deadline = time.monotonic() + deadline_seconds
    last = None
    while time.monotonic() < deadline:
        last = probe()
        if last:
            return last
        time.sleep(3)
    raise RuntimeError(f"timed out waiting for {description}; last={bool(last)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://192.168.0.112:8040")
    parser.add_argument(
        "--feed-url", default="https://news.pinepods.online/feed.xml"
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("/srv/appdata/docker/pinepods/acceptance"),
    )
    args = parser.parse_args()

    username = os.environ["PINEPODS_ADMIN_USERNAME"]
    password = os.environ["PINEPODS_ADMIN_PASSWORD"]
    login, _ = request(
        args.base_url,
        "/api/data/get_key",
        basic=(username, password),
    )
    if login.get("status") != "success" or login.get("mfa_required"):
        raise RuntimeError("supported password login did not return an API key")
    api_key = login["retrieved_key"]
    user_id = int(login["user_id"])

    def podcasts() -> list[dict[str, Any]]:
        value, _ = request(
            args.base_url,
            f"/api/data/return_pods/{user_id}",
            api_key=api_key,
        )
        return value["pods"]

    existing = [item for item in podcasts() if item["feedurl"] == args.feed_url]
    if not existing:
        request(
            args.base_url,
            "/api/data/add_podcast",
            method="POST",
            api_key=api_key,
            data={
                "podcast_values": {
                    "pod_title": "PinePods News",
                    "pod_artwork": "",
                    "pod_author": "PinePods",
                    "categories": {},
                    "pod_description": "Public PinePods acceptance feed",
                    "pod_episode_count": 0,
                    "pod_feed_url": args.feed_url,
                    "pod_website": "https://www.pinepods.online/",
                    "pod_explicit": False,
                    "user_id": user_id,
                },
                "podcast_index_id": 0,
            },
        )

    subscription = wait_until(
        "public-feed subscription",
        180,
        lambda: next(
            (item for item in podcasts() if item["feedurl"] == args.feed_url),
            None,
        ),
    )

    def feed_episodes() -> list[dict[str, Any]]:
        value, _ = request(
            args.base_url,
            f"/api/data/return_episodes/{user_id}?limit=200",
            api_key=api_key,
        )
        return [
            episode
            for episode in value["episodes"]
            if int(episode["podcastid"]) == int(subscription["podcastid"])
        ]

    episodes = wait_until(
        "refreshed public-feed episodes",
        300,
        lambda: feed_episodes() or None,
    )
    episode = episodes[0]

    downloads_enabled, _ = request(
        args.base_url,
        "/api/data/download_status",
        api_key=api_key,
    )
    if downloads_enabled is not True:
        raise RuntimeError("PinePods server downloads are disabled")
    if not episode["downloaded"]:
        request(
            args.base_url,
            "/api/data/download_podcast",
            method="POST",
            api_key=api_key,
            data={
                "episode_id": episode["episodeid"],
                "user_id": user_id,
                "is_youtube": False,
            },
        )

    downloaded = wait_until(
        "episode download",
        600,
        lambda: next(
            (
                item
                for item in feed_episodes()
                if item["episodeid"] == episode["episodeid"]
                and item["downloaded"]
            ),
            None,
        ),
    )

    web_position = min(37, max(1, downloaded["episodeduration"] // 4))
    request(
        args.base_url,
        "/api/data/record_listen_duration",
        method="POST",
        api_key=api_key,
        data={
            "episode_id": episode["episodeid"],
            "user_id": user_id,
            "listen_duration": web_position,
            "is_youtube": False,
        },
    )
    web_resume = wait_until(
        "web progress persistence",
        60,
        lambda: next(
            (
                item
                for item in feed_episodes()
                if item["episodeid"] == episode["episodeid"]
                and int(item.get("listenduration") or 0) == web_position
            ),
            None,
        ),
    )

    exported_opml, opml_bytes = request(
        args.base_url,
        "/api/data/backup_user",
        method="POST",
        api_key=api_key,
        data={"user_id": user_id},
    )
    if args.feed_url not in exported_opml:
        raise RuntimeError("OPML export does not contain the subscribed feed")
    before_import = len(podcasts())
    request(
        args.base_url,
        "/api/data/import_opml",
        method="POST",
        api_key=api_key,
        data={"podcasts": [args.feed_url], "user_id": user_id},
    )
    wait_until(
        "idempotent OPML re-import",
        180,
        lambda: len(podcasts()) == before_import,
    )
    matching_after_import = sum(
        item["feedurl"] == args.feed_url for item in podcasts()
    )
    if matching_after_import != 1:
        raise RuntimeError("OPML re-import duplicated the public subscription")

    request(
        args.base_url,
        "/api/data/gpodder/toggle",
        method="POST",
        api_key=api_key,
        data={"enabled": True},
    )
    device = "phase5-acceptance"
    gpodder_subscriptions, _ = request(
        args.base_url,
        f"/api/2/subscriptions/{username}/{device}.json",
        basic=(username, password),
    )
    if args.feed_url not in gpodder_subscriptions:
        raise RuntimeError("GPodder client did not receive the subscription")

    client_position = min(
        max(web_position + 11, 2),
        max(2, downloaded["episodeduration"] - 1),
    )
    gpodder_response, _ = request(
        args.base_url,
        f"/api/2/episodes/{username}.json",
        method="POST",
        basic=(username, password),
        data=[
            {
                "podcast": args.feed_url,
                "episode": downloaded["episodeurl"],
                "device": device,
                "action": "play",
                "started": 0,
                "position": client_position,
                "total": downloaded["episodeduration"],
            }
        ],
    )
    if not isinstance(gpodder_response, dict):
        raise RuntimeError("GPodder client action returned an invalid response")
    client_resume = wait_until(
        "GPodder progress in the main application API",
        120,
        lambda: next(
            (
                item
                for item in feed_episodes()
                if item["episodeid"] == episode["episodeid"]
                and int(item.get("listenduration") or 0) == client_position
            ),
            None,
        ),
    )

    episode_root = Path("/podcasts/pinepods")
    files = [path for path in episode_root.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    if not files or total_bytes <= 0:
        raise RuntimeError("downloaded episode is absent from PinePods shared storage")

    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    evidence_dir = args.evidence_root / timestamp
    evidence_dir.mkdir(parents=True, mode=0o700)
    summary = {
        "completed_at": timestamp,
        "feed_sha256": hashlib.sha256(args.feed_url.encode()).hexdigest(),
        "user_counted": True,
        "subscription_count": len(podcasts()),
        "matching_test_subscriptions": matching_after_import,
        "episode_count": len(episodes),
        "downloaded_episode_id": int(downloaded["episodeid"]),
        "download_file_count": len(files),
        "download_total_bytes": total_bytes,
        "web_resume_position": int(web_resume["listenduration"]),
        "gpodder_resume_position": int(client_resume["listenduration"]),
        "gpodder_subscription_count": len(gpodder_subscriptions),
        "opml_sha256": hashlib.sha256(opml_bytes).hexdigest(),
        "opml_reimport_duplicate_count": 0,
    }
    evidence_file = evidence_dir / "acceptance-summary.json"
    evidence_file.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence_file.chmod(0o600)
    print(
        "PinePods subscription/download/web-progress/GPodder/OPML acceptance "
        f"passed; evidence={evidence_file}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
