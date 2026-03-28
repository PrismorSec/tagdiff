import hashlib
import json
import time
from pathlib import Path

from tagdiff.config import CACHE_DIR, DEFAULT_CACHE_TTL


def _cache_path(repo, stop_at_tag=None):
    key = repo
    if stop_at_tag:
        key += f":{stop_at_tag}"
    filename = hashlib.sha256(key.encode()).hexdigest()[:16] + ".json"
    return CACHE_DIR / filename


def read_cache(repo, stop_at_tag=None, ttl=DEFAULT_CACHE_TTL):
    path = _cache_path(repo, stop_at_tag)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("cached_at", 0) > ttl:
            return None
        return data["releases"]
    except (json.JSONDecodeError, KeyError):
        return None


def write_cache(repo, releases, stop_at_tag=None):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(repo, stop_at_tag)
    data = {
        "repo": repo,
        "stop_at_tag": stop_at_tag,
        "cached_at": time.time(),
        "releases": releases,
    }
    path.write_text(json.dumps(data))


def clear_cache(repo=None):
    """Clear cached releases. If repo is given, clear only that repo's cache."""
    if not CACHE_DIR.exists():
        return 0
    removed = 0
    if repo:
        for path in CACHE_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("repo") == repo:
                    path.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError):
                pass
    else:
        for path in CACHE_DIR.glob("*.json"):
            path.unlink()
            removed += 1
    return removed
