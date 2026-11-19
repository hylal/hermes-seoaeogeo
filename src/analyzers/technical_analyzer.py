"""Real technical SEO analyzer — fetches live pages and evaluates on-page factors."""

from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup


def _safe_get(url: str, timeout: int = 15, follow_redirects: bool = True) -> requests.Response | None:
    """Fetch a URL safely, following redirects and handling common errors."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Hermes-AEO-GEO/1.0; +https://github.com/hylal/hermes-seoaeogeo)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    }
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=follow_redirects,
            verify=True,
        )
        return resp
    except requests.RequestException as exc:
        print(f"  ⚠️ Fetch failed for {url}: {exc}")
        return None


class TechnicalAnalyzer:
    """Evaluate on-page technical SEO factors from a live URL.

    Checks:
      - Protocol (HTTPS vs HTTP)
      - Title tag (present, length, optimal range)
      - Meta description (present, length)
      - H1 (exactly one?) + heading hierarchy
      - Images with missing alt text
      - Canonical link
      - Open Graph meta tags
      - Structured data (JSON-LD / Microdata)
      - robots.txt & meta robots
      - Page size indicators (link count, word count)
    """

    STATUS_OK = "ok"
    STATUS_WARN = "warn"
    STATUS_ERROR = "error"

    TITLE_OPTIMAL_MIN = 30
    TITLE_OPTIMAL_MAX = 60
    DESC_OPTIMAL_MIN = 120
    DESC_OPTIMAL_MAX = 160

    def __init__(self, timeout: int = 15, use_cache: bool = True, cache_ttl: int = 300) -> None:
        self.timeout = timeout
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self._cache = None
        if use_cache:
            from src.cache import UrlCache
            from src.config import ensure_cache_dir
            self._cache = UrlCache(ensure_cache_dir())

    # ------------------------------------------------------------------ public
    def audit(self, url: str, *, html: str | None = None) -> dict[str, Any]:
        """Run full technical audit against *url*. Returns checklist + score.

        Args:
            url: Page URL to audit.
            html: Optional pre-fetched HTML. When provided, skips the network fetch
                  and parses directly from this string (avoids double-fetching when
                  called alongside other analyzers that also need the raw content).
        """
        # Check cache first (only when doing a real fetch)
        if self._cache is not None and html is None:
            cached = self._cache.get(url, ttl=self.cache_ttl)
            if cached is not None:
                return cached

        if html is None:
            resp = _safe_get(url, timeout=self.timeout)
            if resp is None:
                result = {
                    "score": 0,
                    "checks": [self._check("Fetch", f"Could not reach {url}", self.STATUS_ERROR)],
                    "details": {"final_url": url, "http_code": None},
                }
                if self._cache is not None:
                    self._cache.put(url, result)
                return result

            final_url = resp.url
            http_code = resp.status_code
            soup = BeautifulSoup(resp.text, "html.parser")
            raw_html = resp.text
        else:
            final_url = url
            http_code = 200
            soup = BeautifulSoup(html, "html.parser")
            raw_html = html

        checks: list[dict[str, Any]] = []
        details: dict[str, Any] = {"final_url": final_url, "http_code": http_code}

        # 1. Protocol
        checks.append(self._check_protocol(final_url))

        # 2. HTTP status
        if 200 <= http_code < 400:
            checks.append(self._check("HTTP Status", f"{http_code} OK", self.STATUS_OK))
        elif http_code == 404:
            checks.append(self._check("HTTP Status", "404 Not Found", self.STATUS_ERROR))
        else:
            checks.append(self._check("HTTP Status", str(http_code), self.STATUS_WARN))

        # 3. Title tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title_text = title_tag.string.strip()
            tlen = len(title_text)
            if tlen < self.TITLE_OPTIMAL_MIN:
                checks.append(self._check("Title Tag", f'Short ({tlen} chars): "{title_text}"', self.STATUS_WARN))
            elif tlen > self.TITLE_OPTIMAL_MAX:
                checks.append(self._check("Title Tag", f'Too long ({tlen} chars): truncation likely', self.STATUS_WARN))
            else:
                checks.append(self._check("Title Tag", f'OK ({tlen} chars)', self.STATUS_OK))
            details["title"] = title_text
            details["title_len"] = tlen
        else:
            checks.append(self._check("Title Tag", "Missing", self.STATUS_ERROR))
            details["title"] = ""
            details["title_len"] = 0

        # 4. Meta description
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if desc_meta and desc_meta.get("content"):
            desc = desc_meta["content"].strip()
            dlen = len(desc)
            if dlen < self.DESC_OPTIMAL_MIN:
                checks.append(self._check("Meta Description", f'Short ({dlen} chars)', self.STATUS_WARN))
            elif dlen > self.DESC_OPTIMAL_MAX:
                checks.append(self._check("Meta Description", f'Too long ({dlen} chars)', self.STATUS_WARN))
            else:
                checks.append(self._check("Meta Description", f'OK ({dlen} chars)', self.STATUS_OK))
            details["description"] = desc
            details["desc_len"] = dlen
        else:
            checks.append(self._check("Meta Description", "Missing", self.STATUS_ERROR))

        # 5. H1 count
        h1_tags = soup.find_all("h1")
        if len(h1_tags) == 1:
            checks.append(self._check("H1 Count", "Exactly 1 ✓", self.STATUS_OK))
        elif len(h1_tags) == 0:
            checks.append(self._check("H1 Count", "Missing — required for SEO", self.STATUS_ERROR))
        else:
            checks.append(self._check("H1 Count", f"Multiple ({len(h1_tags)}) — should be exactly 1", self.STATUS_WARN))
        details["h1_count"] = len(h1_tags)

        # 6. Heading hierarchy (H2-H6)
        headings = {}
        for level in range(2, 7):
            tags = soup.find_all(re.compile(f"^h{level}$"))
            headings[level] = len(tags)
        total_headings = sum(headings.values())
        if total_headings >= 3:
            checks.append(self._check("Headings", f"H2-H6: {total_headings} present", self.STATUS_OK))
        else:
            checks.append(self._check("Headings", f"Only {total_headings} — consider more structure", self.STATUS_WARN))
        details["headings"] = headings

        # 7. Image alt attributes
        images = soup.find_all("img")
        img_with_alt = sum(1 for img in images if img.get("alt") and img["alt"].strip())
        img_without_alt = len(images) - img_with_alt
        if images:
            pct = round(img_with_alt / len(images) * 100)
            if pct >= 90:
                checks.append(self._check("Image Alt", f"{img_with_alt}/{len(images)} tagged ({pct}%)", self.STATUS_OK))
            elif pct >= 50:
                checks.append(self._check("Image Alt", f"{img_with_alt}/{len(images)} tagged ({pct}%) — incomplete", self.STATUS_WARN))
            else:
                checks.append(self._check("Image Alt", f"{img_without_alt} images missing alt text", self.STATUS_ERROR))
        else:
            checks.append(self._check("Image Alt", "No <img> tags found", self.STATUS_WARN))
        details["images"] = {"total": len(images), "with_alt": img_with_alt, "without_alt": img_without_alt}

        # 8. Canonical link
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            href = canonical["href"].strip()
            if href.startswith(("http://", "https://")):
                checks.append(self._check("Canonical", f'✓ {href[:60]}{"…" if len(href)>60 else ""}', self.STATUS_OK))
                details["canonical"] = href
            else:
                checks.append(self._check("Canonical", f'Relative path: {href}', self.STATUS_WARN))
                details["canonical"] = href
        else:
            checks.append(self._check("Canonical", "Missing — may cause duplicate-content issues", self.STATUS_WARN))
            details["canonical"] = None

        # 9. Open Graph tags
        og_tags = soup.find_all("meta", attrs={"property": re.compile(r"^og:", re.IGNORECASE)})
        og_props = ["og:title", "og:description", "og:image", "og:url"]
        found_og = [prop for prop in og_props if any(m.get("property","").lower()==prop for m in og_tags)]
        if len(found_og) == 4:
            checks.append(self._check("Open Graph", "All 4 core tags present", self.STATUS_OK))
        elif len(found_og) >= 2:
            checks.append(self._check("Open Graph", f"{len(found_og)}/4 tags: {', '.join(found_og)}", self.STATUS_WARN))
        else:
            checks.append(self._check("Open Graph", "Minimal or missing — social sharing unfriendly", self.STATUS_WARN))
        details["og_tags"] = len(og_tags)

        # 10. Structured data (JSON-LD)
        ld_scripts = soup.find_all("script", type="application/ld+json")
        microdata_items = len(soup.find_all(attrs={"itemscope": True}))
        if ld_scripts:
            checks.append(self._check("Structured Data", f'{len(ld_scripts)} JSON-LD block(s)', self.STATUS_OK))
            details["structured_data_ld"] = len(ld_scripts)
            details["structured_data_microdata"] = microdata_items
            try:
                schemas = []
                for s in ld_scripts:
                    try:
                        import json as _json
                        parsed = _json.loads(s.string or "")
                        if isinstance(parsed, list):
                            schemas.extend([type(x).__name__ for x in parsed])
                        elif isinstance(parsed, dict):
                            schemas.append(parsed.get("@type", "Unknown"))
                    except Exception:
                        schemas.append("(parse error)")
                details["schema_types"] = schemas
            except Exception:
                pass
        elif microdata_items:
            checks.append(self._check("Structured Data", f'{microdata_items} Microdata item(s)', self.STATUS_WARN))
            details["structured_data_ld"] = 0
            details["structured_data_microdata"] = microdata_items
        else:
            checks.append(self._check("Structured Data", "No JSON-LD or Microdata found", self.STATUS_WARN))
            details["structured_data_ld"] = 0
            details["structured_data_microdata"] = 0

        # 11. robots meta tag
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        if robots_meta and robots_meta.get("content"):
            content = robots_meta["content"].lower()
            if "noindex" in content:
                checks.append(self._check("Robots Meta", "Robots meta contains noindex — page won't appear in search", self.STATUS_ERROR))
            elif "nofollow" in content:
                checks.append(self._check("Robots Meta", 'Contains "nofollow"', self.STATUS_WARN))
            else:
                checks.append(self._check("Robots Meta", 'Content: "{}"'.format(robots_meta["content"]), self.STATUS_OK))
            details["robots_meta"] = robots_meta["content"]
        else:
            checks.append(self._check("Robots Meta", "Not set (defaults allow indexing)", self.STATUS_OK))
            details["robots_meta"] = None

        # 12. Content size indicator (word count via body)
        body = soup.find("body")
        text_content = body.get_text(" ", strip=True) if body else soup.get_text(" ", strip=True)
        word_count = len(text_content.split())
        details["word_count"] = word_count
        if word_count >= 300:
            checks.append(self._check("Content Length", f'{word_count} words — sufficient depth', self.STATUS_OK))
        elif word_count >= 100:
            checks.append(self._check("Content Length", f'{word_count} words — thin content risk', self.STATUS_WARN))
        else:
            checks.append(self._check("Content Length", f'{word_count} words — very thin', self.STATUS_ERROR))

        # 13. Link density (internal vs external)
        all_links = soup.find_all("a", href=True)
        internal = sum(1 for a in all_links if a["href"].startswith("/") or a["href"].startswith(final_url))
        external = len(all_links) - internal
        details["links"] = {"total": len(all_links), "internal": internal, "external": external}
        if internal >= 3 and external >= 1:
            checks.append(self._check("Link Balance", f'{internal} internal / {external} external', self.STATUS_OK))
        elif internal == 0:
            checks.append(self._check("Link Balance", "No internal links found", self.STATUS_WARN))
        else:
            checks.append(self._check("Link Balance", f'{len(all_links)} total links', self.STATUS_WARN))

        # Compute overall score (weighted)
        weights = {
            "Protocol": 10, "HTTP Status": 10, "Title Tag": 10,
            "Meta Description": 10, "H1 Count": 10, "Headings": 5,
            "Image Alt": 10, "Canonical": 5, "Open Graph": 5,
            "Structured Data": 10, "Robots Meta": 5,
            "Content Length": 3, "Link Balance": 2,
        }
        total_weight = sum(weights.values())
        earned = 0
        score_details = []
        for ch in checks:
            w = weights.get(ch["check"], 0)
            if ch["status"] == self.STATUS_OK:
                earned += w
            elif ch["status"] == self.STATUS_WARN:
                earned += w * 0.5
            score_details.append({"check": ch["check"], "weight": w, "earned": w if ch["status"] == self.STATUS_OK else (w * 0.5 if ch["status"] == self.STATUS_WARN else 0)})

        final_score = round(earned / total_weight * 100)
        details["score_breakdown"] = score_details
        details["_raw_html"] = raw_html  # expose for reuse by other analyzers
        result = {"score": final_score, "checks": checks, "details": details}
        if self._cache is not None:
            self._cache.put(final_url or url, result)
        return result

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _check(name: str, finding: str, status: str) -> dict[str, Any]:
        return {"check": name, "finding": finding, "status": status}

    @staticmethod
    def _check_protocol(url: str) -> dict[str, Any]:
        if url.startswith("https://"):
            return TechnicalAnalyzer._check("Protocol", "HTTPS enabled ✓", TechnicalAnalyzer.STATUS_OK)
        else:
            return TechnicalAnalyzer._check("Protocol", "HTTP — insecure; upgrade required", TechnicalAnalyzer.STATUS_ERROR)
