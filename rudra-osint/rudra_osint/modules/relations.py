"""Relationship and social connections graph builder."""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from rudra_osint.config import USER_AGENT
from rudra_osint.modules.identity import SocialHit


@dataclass
class TargetRelations:
    target: str
    known_aliases: list[str] = field(default_factory=list)
    linked_urls: list[str] = field(default_factory=list)
    associated_orgs: list[str] = field(default_factory=list)
    collaborators: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    bio_text: str = ""
    location: str = ""


def _fetch_github_profile_deep(username: str) -> Optional[dict]:
    """Query GitHub public user & event API for affiliations, orgs, and collaborators."""
    api_url = f"https://api.github.com/users/{username}"
    req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception:
        return None


def _fetch_github_orgs_and_events(username: str) -> tuple[list[str], list[str]]:
    """Get public orgs and co-contributors/collaborators from public events."""
    orgs = []
    collaborators = set()

    # Orgs
    try:
        req = urllib.request.Request(f"https://api.github.com/users/{username}/orgs", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            org_data = json.loads(resp.read().decode("utf-8"))
            for o in org_data:
                if "login" in o:
                    orgs.append(o["login"])
    except Exception:
        pass

    # Events to find co-authors
    try:
        req = urllib.request.Request(f"https://api.github.com/users/{username}/events/public", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            events = json.loads(resp.read().decode("utf-8"))
            for ev in events[:15]:
                payload = ev.get("payload", {})
                for commit in payload.get("commits", []):
                    author = commit.get("author", {})
                    author_name = author.get("name", "")
                    if author_name and author_name.lower() != username.lower():
                        collaborators.add(author_name)
    except Exception:
        pass

    return orgs, list(collaborators)[:10]


def build_relationships(username: str, social_hits: list[SocialHit]) -> TargetRelations:
    """Build a comprehensive relationship and connection profile for a target."""
    relations = TargetRelations(target=username)

    # 1. Inspect GitHub if present
    gh_hit = next((h for h in social_hits if h.platform.lower() == "github"), None)
    if gh_hit:
        gh_data = _fetch_github_profile_deep(username)
        if gh_data:
            if gh_data.get("name"):
                relations.known_aliases.append(gh_data["name"])
            if gh_data.get("bio"):
                relations.bio_text = gh_data["bio"]
            if gh_data.get("location"):
                relations.location = gh_data["location"]
            if gh_data.get("blog"):
                relations.linked_urls.append(gh_data["blog"])
            if gh_data.get("twitter_username"):
                relations.social_links["Twitter/X"] = f"https://x.com/{gh_data['twitter_username']}"

        orgs, collabs = _fetch_github_orgs_and_events(username)
        relations.associated_orgs.extend(orgs)
        relations.collaborators.extend(collabs)

    # 2. Extract social links from hits
    for hit in social_hits:
        relations.social_links[hit.platform] = hit.url

    # Deduplicate
    relations.known_aliases = list(dict.fromkeys(relations.known_aliases))
    relations.linked_urls = list(dict.fromkeys(relations.linked_urls))
    relations.associated_orgs = list(dict.fromkeys(relations.associated_orgs))
    relations.collaborators = list(dict.fromkeys(relations.collaborators))

    return relations
