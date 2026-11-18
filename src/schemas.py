"""Tool schemas — what the LLM reads to decide when to call our tools."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# seo_audit — full SEO / AEO / GEO audit
# ---------------------------------------------------------------------------
SEOAUDIT_SCHEMA = {
    "name": "seo_audit",
    "description": (
        "Run a comprehensive SEO / AEO / GEO audit on a URL. Use this when you need "
        "to analyze a page for technical issues, answer-engine opportunities, or "
        "LLM citability. Always prefer this for marketing pages, blog posts, and "
        "product pages before publishing or updating content."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to audit (e.g., https://myleben.co.id/some-post).",
            },
            "mode": {
                "type": "string",
                "enum": ["full", "technical", "aeo", "geo"],
                "description": "Audit mode. 'full' covers all three dimensions; use a specific mode to narrow focus.",
                "default": "full",
            },
        },
        "required": ["url"],
    },
}

# ---------------------------------------------------------------------------
# wp_schema_apply — generate JSON-LD / WP REST API payload
# ---------------------------------------------------------------------------
WPSCHEMA_SCHEMA = {
    "name": "wp_schema_apply",
    "description": (
        "Generate a JSON-LD structured data snippet and a WordPress REST API "
        "payload for the given schema type. This tool does NOT modify your site — "
        "it only provides the code/NPX you execute via WP-CLI or the REST API. "
        "Use it after an seo_audit reveals a missing or incomplete schema."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The target page URL.",
            },
            "schema_type": {
                "type": "string",
                "enum": ["Article", "FAQPage", "HowTo", "LocalBusiness", "Product"],
                "description": "The schema type to generate.",
                "default": "Article",
            },
            "output": {
                "type": "string",
                "enum": ["json", "payload"],
                "description": "Output format: 'json' prints JSON-LD; 'payload' prints a WP REST API POST body.",
                "default": "json",
            },
        },
        "required": ["url"],
    },
}

# ---------------------------------------------------------------------------
# get_aeo_opportunities — conversational query extraction
# ---------------------------------------------------------------------------
AEOPPA_SCHEMA = {
    "name": "get_aeo_opportunities",
    "description": (
        "Extract People Also Ask (PAA) items and conversational queries from a "
        "URL, then suggest FAQPage or QAPage schema additions to capture featured "
        "snippet and voice search traffic. Use this after publishing a long-form "
        "article to round out the Q&A coverage."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The page URL to scan for PAA queries.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of opportunities to return (default 10).",
                "default": 10,
            },
        },
        "required": ["url"],
    },
}
