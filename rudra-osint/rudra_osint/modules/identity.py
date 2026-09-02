"""Identity and social footprint discovery module."""

from __future__ import annotations

import concurrent.futures
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional

from rudra_osint.config import PLATFORMS, USER_AGENT


@dataclass
class SocialHit:
    platform: str
    url: str
    category: str
    status_code: int = 200
    bio: str = ""
    extracted_links: list[str] = field(default_factory=list)
    location: str = ""
    full_name: str = ""


def _fetch(url: str, timeout: int = 5) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            text = content.decode("utf-8", errors="replace")
            return resp.status, text, content
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, body, b""
    except Exception:
        return 0, "", b""


def _check_single_platform(platform_name: str, pdata: dict, username: str) -> Optional[SocialHit]:
    url = pdata["url"].format(username=username)
    check_type = pdata.get("check_type", "status")
    profile_url = pdata.get("profile_url", url).format(username=username)
    category = pdata.get("category", "General")

    code, text, _ = _fetch(url, timeout=6)

    if check_type == "status":
        if code in (200, 301, 302):
            return SocialHit(platform=platform_name, url=profile_url, category=category, status_code=code)
    elif check_type == "json_reddit":
        if code == 200:
            try:
                data = json.loads(text)
                if "data" in data and "name" in data["data"]:
                    return SocialHit(platform=platform_name, url=profile_url, category=category, status_code=200)
            except Exception:
                pass
    elif check_type == "json_hn":
        if code == 200 and text.strip() != "null":
            return SocialHit(platform=platform_name, url=profile_url, category=category, status_code=200)
    elif check_type == "body_not_contains":
        not_contains = pdata.get("not_contains", "")
        if code == 200 and not_contains not in text:
            return SocialHit(platform=platform_name, url=profile_url, category=category, status_code=200)

    return None


def scan_username(
    username: str,
    platform_hint: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[SocialHit]:
    """Scan username across social and developer platforms in parallel."""
    username = username.strip().lstrip("@")
    targets = {}

    if platform_hint:
        hint_lower = platform_hint.lower()
        for p, d in PLATFORMS.items():
            if hint_lower in p.lower():
                targets[p] = d
        if not targets:
            targets = PLATFORMS
    else:
        targets = PLATFORMS

    results: list[SocialHit] = []
    total = len(targets)
    completed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_platform = {
            executor.submit(_check_single_platform, p, d, username): p
            for p, d in targets.items()
        }

        for future in concurrent.futures.as_completed(future_to_platform):
            completed += 1
            p_name = future_to_platform[future]
            if progress_callback:
                progress_callback(completed, total, p_name)

            try:
                hit = future.result()
                if hit:
                    results.append(hit)
            except Exception:
                pass

    return sorted(results, key=lambda x: (x.category, x.platform))
