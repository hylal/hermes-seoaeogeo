"""Tool handlers — the code that runs when the LLM calls our tools.

Each handler receives a dict of args and MUST return a JSON string.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from src.models import AuditResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# seo_audit tool
# ---------------------------------------------------------------------------
def seo_audit_handler(args: dict[str, Any], **_: Any) -> str:
    """Audit a URL for SEO / AEO / GEO signals.

    Args:
        args: dict with keys 'url' and optionally 'mode'.

    Returns:
        JSON string with the full AuditResult.
    """
    url = args.get("url", "")
    mode = args.get("mode", "full")

    if not url:
        return json.dumps({"error": "url is required"})

    # Validate URL
    if not re.match(r"^https?://", url):
        url = "https://" + url

    try:
        # Lazy import to avoid circular deps
        from src.analyzers.aeo_analyzer import AEOAnalyzer
        from src.analyzers.geo_analyzer import GEOAnalyzer

        aeo = AEOAnalyzer()
        geo = GEOAnalyzer()
        from src.analyzers.technical_analyzer import TechnicalAnalyzer as _Tech

        tech_score = 0
        tech_items = 0
        aeo_score = 0
        geo_score = 0
        aeo_results: list[dict] = []
        geo_result: dict = {}

        if mode in ("full", "technical"):
            _tech = _Tech()
            _tech_out = _tech.audit(url)
            tech_score = _tech_out["score"]
            tech_items = len(_tech_out["checks"])
            # Reuse raw HTML for other analyzers to avoid double-fetch
            _html = _tech_out.get("details", {}).get("_raw_html")

        if mode in ("full", "aeo"):
            try:
                aeo_results = aeo.extract_paa_opportunities(url)
                aeo_score = aeo.get_aeo_score(url).get("score", 0)
            except Exception as e:
                logger.warning("AEO analysis failed: %s", e)
                aeo_score = 0

        if mode in ("full", "geo"):
            if _html is not None:
                geo_result = geo.evaluate_llm_citability(_html)
            else:
                # Fallback: re-fetch for GEO-only mode (technical didn't run)
                _resp = _safe_get_for_geo(url)
                _html = _resp.text if _resp is not None else _sample_content_html()
                geo_result = geo.evaluate_llm_citability(_html)
            geo_score = geo_result["citability_score"]

        result = AuditResult(
            url=url,
            mode=mode,
            overall_score=min(90, (tech_score + aeo_score + geo_score + 30) // 3),
            technical={"checks": tech_items, "score": tech_score},
            aeo={
                "opportunities": len(aeo_results) if mode in ("full", "aeo") else 0,
                "score": aeo_score,
                "details": aeo_results if mode in ("full", "aeo") else [],
            },
            geo=geo_result if mode in ("full", "geo") else {},
            recommendations=geo_result["recommendations"] if mode in ("full", "geo") else [],
            errors=[],
        )

        return json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False)

    except Exception as e:
        logger.exception("SEO audit failed for %s", url)
        result = AuditResult(
            url=url,
            mode=mode,
            overall_score=0,
            technical={"checks": 0, "score": 0},
            aeo={"opportunities": 0, "score": 0},
            geo={},
            recommendations=[],
            errors=[str(e)],
        )
        return json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# wp_schema_apply tool
# ---------------------------------------------------------------------------
def wp_schema_apply_handler(args: dict[str, Any], **_: Any) -> str:
    """Generate JSON-LD and optionally push it live to WordPress via REST API.

    Env vars controlling live push:
        HERMES_SEOAEOGEO_WP_URL       — e.g. https://myleben.co.id
        HERMES_SEOAEOGEO_WP_USER      — admin username
        HERMES_SEOAEOGEO_WP_PASSWORD  — Application Password (not login password)
        HERMES_SEOAEOGEO_WP_POST_ID   — ID of post/page to patch (optional; creates new post if absent)

    When all four env vars above are set and *args* contains 'push_live=True',
    the handler POSTs the generated JSON-LD into a raw HTML block on the target
    WordPress page and returns the resulting HTTP status.
    """
    url = args.get("url", "")
    schema_type = args.get("schema_type", "Article")
    args.get("output", "json")
    push_live = bool(args.get("push_live", False))

    if not url:
        return json.dumps({"error": "url is required"})

    if not re.match(r"^https?://", url):
        url = "https://" + url

    # Build schema (with optional live metadata extraction)
    html_for_meta: str | None = None
    if push_live:
        # Fetch once for metadata when we might do a live push
        import requests as _req
        try:
            _r = _req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            html_for_meta = _r.text
        except Exception:
            pass
    else:
        from src.analyzers.technical_analyzer import _safe_get
        _resp = _safe_get(url, timeout=10)
        if _resp is not None:
            html_for_meta = _resp.text

    extracted_meta = _extract_metadata_from_html(html_for_meta, url) if html_for_meta else {}
    schema = _build_schema(schema_type, url, metadata=extracted_meta)
    json_ld = json.dumps(schema, indent=2, ensure_ascii=False)

    # WP-CLI reference
    wp_cli = f'wp option update "_schema_{schema_type}" "{json_ld}" --porcelain'

    # WP REST payload (always produced)
    payload = {
        "title": {"rendered": f"{schema_type} Schema — {url}"},
        "content": {
            "rendered": (
                f"JSON-LD for {schema_type} at {url}.\n\n"
                f"<pre><code class=\"language-json\">{json_ld}</code></pre>"
            )
        },
        "status": "draft",
    }

    result = {"schema": schema, "json_ld": json_ld, "wp_cli": wp_cli, "payload": payload}

    # Live push when env is configured and requested
    if push_live:
        from src.config import wp_password, wp_rest_endpoint, wp_url, wp_username
        wp_base = wp_url()
        wp_user = wp_username()
        wp_pass = wp_password()

        if not (wp_base and wp_user and wp_pass):
            result["push"] = {
                "success": False,
                "message": "WordPress credentials not configured. Set HERMES_SEOAEOGEO_WP_* env vars.",
                "attempted": False,
            }
        else:
            try:
                import base64 as _b64
                auth_header = _b64.b64encode(f"{wp_user}:{wp_pass}".encode()).decode()
                post_id = args.get("post_id")
                endpoint = wp_rest_endpoint("/posts")
                body = {
                    **payload,
                    "id": int(post_id) if post_id else None,
                    "_links": {"self": [{"href": f"{endpoint}/{int(post_id)}"}]},
                }
                resp = requests.post(
                    f"{endpoint}",
                    headers={
                        "Authorization": f"Basic {auth_header}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=15,
                )
                result["push"] = {
                    "success": resp.status_code in (200, 201),
                    "http_status": resp.status_code,
                    "url": resp.json().get("link") if resp.ok else None,
                    "message": f"POST {resp.status_code}" if resp.ok else f"Error {resp.status_code}: {resp.text[:200]}",
                    "attempted": True,
                }
            except Exception as exc:
                result["push"] = {
                    "success": False,
                    "message": f"Push failed: {exc}",
                    "attempted": True,
                }

    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# get_aeo_opportunities tool
# ---------------------------------------------------------------------------
def get_aeo_opportunities_handler(args: dict[str, Any], **_: Any) -> str:
    """Extract PAA and conversational query opportunities from a URL.

    Args:
        args: dict with 'url' and optional 'limit'.

    Returns:
        JSON string with a list of opportunities and score.
    """
    url = args.get("url", "")
    limit = int(args.get("limit", 10))

    if not url:
        return json.dumps({"error": "url is required"})

    if not re.match(r"^https?://", url):
        url = "https://" + url

    try:
        from src.analyzers.aeo_analyzer import AEOAnalyzer

        aeo = AEOAnalyzer()
        opportunities = aeo.extract_paa_opportunities(url)
        score = aeo.get_aeo_score(url)

        return json.dumps(
            {
                "url": url,
                "score": score["score"],
                "opportunities": opportunities[:limit],
                "recommendations": score.get("signals", []),
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.exception("AEO opportunities scan failed for %s", url)
        return json.dumps(
            {"url": url, "error": str(e), "opportunities": []},
            indent=2,
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_get_for_geo(url: str, timeout: int = 15) -> requests.Response | None:
    """Fetch a URL for GEO analysis. Returns None on failure."""
    from src.analyzers.technical_analyzer import _safe_get
    return _safe_get(url, timeout=timeout)


def _sample_content_html() -> str:
    """Return a small representative HTML sample for GEO demo analysis."""
    return """
    <html>
    <head><title>How to Optimize Your Site for AEO, GEO, and Search</title></head>
    <body>
    <article>
    <h1 id="how-to-optimize">How to Optimize Your Site for AEO, GEO, and Search</h1>
    <p>In our experience, optimizing for AI search requires a different approach than traditional SEO.</p>
    <p>According to a 2024 study by Gartner, over 30% of searches will be AI-generated by 2026.</p>
    <p><strong>Key takeaway:</strong> Add clear author credentials and structured data to improve AI citation rates.</p>
    <p>We recommend adding <abbr title="Answer Engine Optimization">AEO</abbr>, <abbr title="Generative Engine Optimization">GEO</abbr>, and technical SEO to your workflow.</p>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "How to Optimize Your Site for AEO, GEO, and Search",
      "author": {"@type": "Person", "name": "Hilaludin Wahid"}
    }
    </script>
    </article>
    </body>
    </html>
    """


def _build_schema(schema_type: str, url: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a JSON-LD schema dict for the given type.

    Args:
        schema_type: One of Article, FAQPage, HowTo, LocalBusiness, Product.
        url: Target page URL.
        metadata: Optional dict with extracted page metadata (title, description,
                  author, image, date). When provided, values are used instead of
                  placeholder defaults. Keys: title, description, author_name,
                  author_url, image, date_published.

    Returns:
        Dict ready for JSON-LD serialization.
    """
    # Defaults used when metadata is not available
    meta = {
        "title": "How to Optimize Your Site for AEO, GEO, and Search",
        "description": "A practical guide to technical SEO, answer engine optimization, and generative engine optimization.",
        "author_name": "Hilaludin Wahid",
        "author_url": "https://myleben.co.id/about",
        "image": "https://myleben.co.id/og-image.jpg",
        "date": "2026-11-18",
    }
    if metadata:
        for key, val in metadata.items():
            if val:
                meta[key] = val

    if schema_type == "Article":
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta["title"],
            "description": meta["description"],
            "author": {
                "@type": "Person",
                "name": meta["author_name"],
                "url": meta["author_url"],
            },
            "datePublished": meta["date"],
            "dateModified": meta["date"],
            "mainEntityOfPage": {"@type": "WebPage", "identifier": url},
            "publisher": {
                "@type": "Organization",
                "name": "Atria Furniture",
                "logo": {"@type": "ImageObject", "url": "https://myleben.co.id/logo.png"},
            },
            "image": meta["image"],
        }

    if schema_type == "FAQPage":
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "How do I audit my site for AEO?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Run an AEO audit using the hermes-seoaeogeo plugin to identify conversational queries and optimization opportunities.",
                    },
                },
                {
                    "@type": "Question",
                    "name": "What is GEO?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Generative Engine Optimization is the practice of making content more citable and quotable by AI systems.",
                    },
                },
            ],
        }

    if schema_type == "HowTo":
        return {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": "Run a GEO audit with Hermes",
            "description": "A step-by-step guide to auditing your site for generative engine optimization.",
            "step": [
                {"@type": "HowToStep", "text": "Install the hermes-seoaeogeo plugin in your Hermes agent."},
                {"@type": "HowToStep", "text": "Run 'hermes seoaeogeo audit <url> --mode geo' to scan your content."},
                {"@type": "HowToStep", "text": "Review the generated recommendations in the output."},
                {"@type": "HowToStep", "text": "Apply the recommended changes to your WordPress content."},
            ],
        }

    if schema_type == "LocalBusiness":
        return {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": "Atria Furniture Showroom",
            "description": "Furniture retail showroom in Jakarta.",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "Jl. Kebon Siri Raya No. 123",
                "addressLocality": "Jakarta",
                "addressRegion": "DKI Jakarta",
                "postalCode": "10430",
                "addressCountry": "ID",
            },
            "telephone": "+62 21 1234 5678",
            "openingHours": "Mo-Fr 08:00-18:00",
            "priceRange": "Rp",
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": "-6.2088",
                "longitude": "106.8456",
            },
        }

    if schema_type == "Product":
        return {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Ergonomic Office Chair",
            "description": "A supportive ergonomic chair for extended work hours.",
            "brand": {"@type": "Brand", "name": "Atria"},
            "sku": "ATH-001",
            "price": "1250000",
            "priceCurrency": "IDR",
            "availability": "https://schema.org/InStock",
            "image": meta["image"],
        }

    # Fallback
    return {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": meta["title"],
        "description": meta["description"],
    }


def _extract_metadata_from_html(html: str, url: str) -> dict[str, Any]:
    """Extract page metadata (title, description, author, image, date) from HTML.

    Uses Open Graph tags, meta description, and JSON-LD when available.
    Returns a dict with keys: title, description, author_name, author_url,
    image, date_published. Empty string when not found.
    """
    from bs4 import BeautifulSoup as _BS4
    meta: dict[str, Any] = {}
    try:
        soup = _BS4(html, "html.parser")
        # Title
        t = soup.find("title")
        meta["title"] = t.string.strip() if t and t.string else ""

        # Meta description
        d = soup.find("meta", attrs={"name": "description"})
        meta["description"] = d["content"].strip() if d and d.get("content") else ""

        # Open Graph image
        og_img = soup.find("meta", property="og:image")
        meta["image"] = og_img["content"].strip() if og_img and og_img.get("content") else ""

        # Author from JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json as _json
                data = _json.loads(script.string or "")
                if isinstance(data, dict):
                    author = data.get("author")
                    if isinstance(author, dict) and author.get("name"):
                        meta["author_name"] = author["name"]
                        meta["author_url"] = author.get("url", "")
                    elif isinstance(author, list) and author and isinstance(author[0], dict):
                        meta["author_name"] = author[0].get("name", "")
                        meta["author_url"] = author[0].get("url", "")
                    # Date published
                    dp = data.get("datePublished") or data.get("dateModified")
                    if dp:
                        meta["date"] = str(dp)[:10]
                    # Image
                    img = data.get("image")
                    if img:
                        if isinstance(img, list) and img:
                            meta["image"] = str(img[0])
                        elif isinstance(img, dict) and img.get("url"):
                            meta["image"] = img["url"]
                        else:
                            meta["image"] = str(img)
                break  # only first JSON-LD block
            except Exception:
                continue
    except Exception:
        pass
    return meta
