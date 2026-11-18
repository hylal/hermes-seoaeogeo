"""Environment-based configuration loader for hermes-seoaeogeo.

Supports optional env vars so users can plug in API keys and WP credentials
without modifying source code.

Env vars:
  HERMES_SEOAEOGEO_WP_URL       WordPress site URL (e.g. https://example.com)
  HERMES_SEOAEOGEO_WP_USER      WP admin username
  HERMES_SEOAEOGEO_WP_PASSWORD  WP Application Password (not account password)
  HERMES_SEOAEOGEO_DATAFORSEO   DataForSEO API key
  HERMES_SEOAEOGEO_CACHE_DIR    Local cache directory (default: ~/.cache/seoaeogeo)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# --------------------------------------------------------------------------- WordPress
def wp_url() -> str:
    return get_env("HERMES_SEOAEOGEO_WP_URL")


def wp_username() -> str:
    return get_env("HERMES_SEOAEOGEO_WP_USER")


def wp_password() -> str:
    return get_env("HERMES_SEOAEOGEO_WP_PASSWORD")


def wp_is_configured() -> bool:
    return bool(wp_url() and wp_username() and wp_password())


def wp_rest_endpoint(suffix: str = "/posts") -> str:
    base = wp_url().rstrip("/")
    return f"{base}/wp-json/wp/v2{suffix}"


# --------------------------------------------------------------------------- DataForSEO
def dataforseo_api_key() -> str:
    return get_env("HERMES_SEOAEOGEO_DATAFORSEO")


# --------------------------------------------------------------------------- Cache
def cache_dir() -> Path:
    home = Path.home()
    dir_name = get_env("HERMES_SEOAEOGEO_CACHE_DIR", str(home / ".cache" / "seoaeogeo"))
    return Path(dir_name)


def ensure_cache_dir() -> Path:
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- Summary
def config_summary() -> dict:
    return {
        "wordpress": {
            "configured": wp_is_configured(),
            "url": wp_url() or "(not set)",
            "username": wp_username() or "(not set)",
        },
        "dataforseo": {
            "configured": bool(dataforseo_api_key()),
            "key_prefix": f"{dataforseo_api_key()[:4]}..." if dataforseo_api_key() else "(not set)",
        },
        "cache": str(ensure_cache_dir()),
    }
