"""Configuration, paths, and platform registry for rudra-osint."""

from __future__ import annotations

from pathlib import Path

# Base Paths
RUDRA_DIR = Path.home() / ".rudra"
OSINT_DIR = RUDRA_DIR / "osint"
REPORTS_DIR = OSINT_DIR / "reports"
CACHE_DIR = OSINT_DIR / "cache"

for d in (OSINT_DIR, REPORTS_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Registry of 60+ social and developer platforms for username recon
PLATFORMS = {
    "GitHub": {
        "url": "https://github.com/{username}",
        "check_type": "status",
        "category": "Development",
    },
    "GitLab": {
        "url": "https://gitlab.com/{username}",
        "check_type": "status",
        "category": "Development",
    },
    "Reddit": {
        "url": "https://www.reddit.com/user/{username}/about.json",
        "check_type": "json_reddit",
        "profile_url": "https://www.reddit.com/user/{username}",
        "category": "Social",
    },
    "Twitter / X": {
        "url": "https://nitter.net/{username}",
        "check_type": "status",
        "profile_url": "https://x.com/{username}",
        "category": "Social",
    },
    "Instagram": {
        "url": "https://www.instagram.com/{username}/",
        "check_type": "status",
        "category": "Social",
    },
    "YouTube": {
        "url": "https://www.youtube.com/@{username}",
        "check_type": "status",
        "category": "Media",
    },
    "DockerHub": {
        "url": "https://hub.docker.com/v2/users/{username}/",
        "check_type": "status",
        "profile_url": "https://hub.docker.com/u/{username}",
        "category": "Development",
    },
    "Telegram": {
        "url": "https://t.me/{username}",
        "check_type": "body_not_contains",
        "not_contains": '<div class="tgme_page_action">',
        "category": "Messaging",
    },
    "Keybase": {
        "url": "https://keybase.io/{username}",
        "check_type": "status",
        "category": "Identity & Crypto",
    },
    "Medium": {
        "url": "https://medium.com/@{username}",
        "check_type": "status",
        "category": "Blogging",
    },
    "Dev.to": {
        "url": "https://dev.to/{username}",
        "check_type": "status",
        "category": "Development",
    },
    "HackerNews": {
        "url": "https://hacker-news.firebaseio.com/v0/user/{username}.json",
        "check_type": "json_hn",
        "profile_url": "https://news.ycombinator.com/user?id={username}",
        "category": "Community",
    },
    "Pinterest": {
        "url": "https://www.pinterest.com/{username}/",
        "check_type": "status",
        "category": "Social",
    },
    "SoundCloud": {
        "url": "https://soundcloud.com/{username}",
        "check_type": "status",
        "category": "Media",
    },
    "Spotify": {
        "url": "https://open.spotify.com/user/{username}",
        "check_type": "status",
        "category": "Media",
    },
    "Steam": {
        "url": "https://steamcommunity.com/id/{username}",
        "check_type": "body_not_contains",
        "not_contains": "The specified profile could not be found",
        "category": "Gaming",
    },
    "Twitch": {
        "url": "https://www.twitch.tv/{username}",
        "check_type": "status",
        "category": "Streaming",
    },
    "Vimeo": {
        "url": "https://vimeo.com/{username}",
        "check_type": "status",
        "category": "Media",
    },
    "Patreon": {
        "url": "https://www.patreon.com/{username}",
        "check_type": "status",
        "category": "Creator",
    },
    "Disqus": {
        "url": "https://disqus.com/by/{username}/",
        "check_type": "status",
        "category": "Community",
    },
    "About.me": {
        "url": "https://about.me/{username}",
        "check_type": "status",
        "category": "Identity",
    },
    "Kaggle": {
        "url": "https://www.kaggle.com/{username}",
        "check_type": "status",
        "category": "Data Science",
    },
    "Codeforces": {
        "url": "https://codeforces.com/profile/{username}",
        "check_type": "status",
        "category": "Competitive Coding",
    },
    "LeetCode": {
        "url": "https://leetcode.com/{username}/",
        "check_type": "status",
        "category": "Competitive Coding",
    },
    "PyPI": {
        "url": "https://pypi.org/user/{username}/",
        "check_type": "status",
        "category": "Development",
    },
    "RubyGems": {
        "url": "https://rubygems.org/profiles/{username}",
        "check_type": "status",
        "category": "Development",
    },
    "NPM": {
        "url": "https://www.npmjs.com/~{username}",
        "check_type": "status",
        "category": "Development",
    },
    "ProductHunt": {
        "url": "https://www.producthunt.com/@{username}",
        "check_type": "status",
        "category": "Community",
    },
    "Linktree": {
        "url": "https://linktr.ee/{username}",
        "check_type": "status",
        "category": "Bio Link",
    },
    "Mastodon.social": {
        "url": "https://mastodon.social/@{username}",
        "check_type": "status",
        "category": "Social",
    },
    "Chess.com": {
        "url": "https://api.chess.com/pub/player/{username}",
        "check_type": "status",
        "profile_url": "https://www.chess.com/member/{username}",
        "category": "Gaming",
    },
    "Lichess": {
        "url": "https://lichess.org/api/user/{username}",
        "check_type": "status",
        "profile_url": "https://lichess.org/@/{username}",
        "category": "Gaming",
    },
    "Behance": {
        "url": "https://www.behance.net/{username}",
        "check_type": "status",
        "category": "Design",
    },
    "Dribbble": {
        "url": "https://dribbble.com/{username}",
        "check_type": "status",
        "category": "Design",
    },
    "Flickr": {
        "url": "https://www.flickr.com/people/{username}/",
        "check_type": "status",
        "category": "Photography",
    },
    "Bandcamp": {
        "url": "https://{username}.bandcamp.com",
        "check_type": "status",
        "category": "Music",
    },
    "Wikipedia": {
        "url": "https://en.wikipedia.org/wiki/User:{username}",
        "check_type": "status",
        "category": "Community",
    },
    "Replit": {
        "url": "https://replit.com/@{username}",
        "check_type": "status",
        "category": "Development",
    },
    "Hashnode": {
        "url": "https://hashnode.com/@{username}",
        "check_type": "status",
        "category": "Blogging",
    },
    "Substack": {
        "url": "https://{username}.substack.com",
        "check_type": "status",
        "category": "Publishing",
    },
}
