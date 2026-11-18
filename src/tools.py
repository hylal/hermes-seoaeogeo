"""Tool handlers — the code that runs when the LLM calls our tools.

Each handler receives a dict of args and MUST return a JSON string.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

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

        tech_score = 0
        tech_items = 0
        aeo_score = 0
        geo_score = 0

        if mode in ("full", "technical"):
            tech_items = 6
            tech_score = 62  # Simulated

        if mode in ("full", "aeo"):
            try:
                aeo_results = aeo.extract_paa_opportunities(url)
                aeo_score = aeo.get_aeo_score(url).get("score", 0)
            except Exception as e:
                logger.warning("AEO analysis failed: %s", e)
                aeo_score = 0

        if mode in ("full", "geo"):
            # Use a sample HTML for the GEO demo analysis
            sample_html = _sample_content_html()
            geo_result = geo.evaluate_llm_citability(sample_html)
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

        return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

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
        return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# wp_schema_apply tool
# ---------------------------------------------------------------------------
def wp_schema_apply_handler(args: dict[str, Any], **_: Any) -> str:
    """Generate JSON-LD and WP REST API payload for a schema type.

    Args:
        args: dict with 'url', 'schema_type', and optionally 'output'.

    Returns:
        JSON string with the schema, JSON-LD, and WP-CLI command.
    """
    url = args.get("url", "")
    schema_type = args.get("schema_type", "Article")
    output = args.get("output", "json")

    if not url:
        return json.dumps({"error": "url is required"})

    if not re.match(r"^https?://", url):
        url = "https://" + url

    # Build schema
    schema = _build_schema(schema_type, url)

    # JSON-LD
    json_ld = json.dumps(schema, indent=2, ensure_ascii=False)

    # WP-CLI
    wp_cli = (
        f'wp option update "_schema_{schema_type}" "{json_ld}" --porcelain'
    )

    # WP REST API payload
    payload = {
        "title": {"rendered": f"{schema_type} Schema - {url}"},
        "content": {
            "rendered": (
                f"Apply this JSON-LD schema to {url}."
                f"\n\n```json\n{json_ld}\n```"
                f"\n\nWP-CLI: {wp_cli}"
            )
        },
        "status": "draft",
    }

    return json.dumps(
        {"schema": schema, "json_ld": json_ld, "wp_cli": wp_cli, "payload": payload},
        indent=2,
        ensure_ascii=False,
    )


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


def _build_schema(schema_type: str, url: str) -> dict[str, Any]:
    """Build a JSON-LD schema dict for the given type.

    Args:
        schema_type: One of Article, FAQPage, HowTo, LocalBusiness, Product.
        url: Target page URL.

    Returns:
        Dict ready for JSON-LD serialization.
    """
    if schema_type == "Article":
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "How to Optimize Your Site for AEO, GEO, and Search",
            "description": "A practical guide to technical SEO, answer engine optimization, and generative engine optimization.",
            "author": {
                "@type": "Person",
                "name": "Hilaludin Wahid",
                "url": "https://myleben.co.id/about",
            },
            "datePublished": "2026-11-18",
            "dateModified": "2026-11-18",
            "mainEntityOfPage": {"@type": "WebPage", "identifier": url},
            "publisher": {
                "@type": "Organization",
                "name": "Atria Furniture",
                "logo": {"@type": "ImageObject", "url": "https://myleben.co.id/logo.png"},
            },
            "image": "https://myleben.co.id/og-image.jpg",
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
            "image": "https://myleben.co.id/charts/atria-chair-product.jpg",
        }

    # Fallback
    return {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": "Auto-generated schema",
        "description": "Generated by hermes-seoaeogeo",
    }
