"""Lightweight cache for URL fetches — stores last response by URL."""

from __future__ import annotations

import json
import time
from pathlib import Path


class UrlCache:
    """Simple file-based LRU-ish cache keyed by URL.

    Each entry stores JSON metadata + raw response body.
    TTL defaults to 300 s (5 min) but can be overridden per call.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ public
    def get(self, url: str, ttl: int = 300) -> dict | None:
        """Return cached response dict or None if miss/expired."""
        key = self._key(url)
        fpath = self._root / key
        if not fpath.exists():
            return None
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            return None
        if time.time() - data["ts"] > ttl:
            return None
        return data["resp"]

    def put(self, url: str, resp: dict) -> None:
        """Store *resp* under *url*. Never fails; silently drops on I/O errors."""
        try:
            key = self._key(url)
            payload = {"ts": time.time(), "resp": resp}
            (self._root / key).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _key(url: str) -> str:
        import hashlib
        h = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{h}.json"

    def prune_expired(self, ttl: int = 86400) -> int:
        """Remove all entries older than *ttl* seconds. Returns count removed."""
        now = time.time()
        count = 0
        for p in self._root.glob("*.json"):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                if now - d.get("ts", 0) > ttl:
                    p.unlink()
                    count += 1
            except Exception:
                count += 1
        return count
