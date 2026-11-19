"""Registration hub for the hermes-seoaeogeo plugin.

Feeds the Hermes Agent plugin registry with tools and hooks so they appear in
your agent's tool roster. The `register(ctx)` entry point is what Hermes calls
when the plugin is linked.

The CLI can also be used standalone: `python -m src.main` or the `seoaeogeo`
console script (when installed via `pip install -e .`).
"""

from __future__ import annotations

import logging
from typing import Any

# Lazy imports so the plugin loads even without Hermes installed
logger = logging.getLogger(__name__)

# Tool schemas (what the agent reads to decide when to call tools)
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "seo_audit": {
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
    },
    "wp_schema_apply": {
        "name": "wp_schema_apply",
        "description": (
            "Generate a JSON-LD structured data snippet and a WordPress REST API "
            "payload for the given schema type. This tool does NOT modify your site — "
            "it only provides the code/Python you execute via WP-CLI or the REST API. "
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
    },
    "get_aeo_opportunities": {
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
    },
}

# Hook registration
HOOKS: dict[str, callable] = {
    "pre_tool_call": None,  # lazy import
}

# Tool implementations (the code that runs when the LLM calls the tool)
TOOL_HANDLERS: dict[str, callable] = {
    "seo_audit": None,  # lazy import from src.tools
    "wp_schema_apply": None,
    "get_aeo_opportunities": None,
}


def _import_tools_handlers() -> None:
    """Import tool handlers lazily so the plugin works without Hermes installed."""
    from src.tools import (
        get_aeo_opportunities_handler,
        seo_audit_handler,
        wp_schema_apply_handler,
    )
    TOOL_HANDLERS["seo_audit"] = seo_audit_handler
    TOOL_HANDLERS["wp_schema_apply"] = wp_schema_apply_handler
    TOOL_HANDLERS["get_aeo_opportunities"] = get_aeo_opportunities_handler


def _import_pre_tool_call_hook() -> None:
    """Import pre_tool_call hook lazily."""
    from src.cli_hooks import on_pre_tool_call
    HOOKS["pre_tool_call"] = on_pre_tool_call


def register(ctx: Any | None = None) -> None:
    """Register all tools and hooks with the Hermes context.

    Args:
        ctx: The Hermes plugin context (provided automatically by Hermes).
              Optional — the plugin also works standalone.
    """
    # Lazy-import handlers (works standalone and inside Hermes)
    _import_tools_handlers()
    _import_pre_tool_call_hook()

    if ctx is not None:
        # Register tools
        for tool_name, tool_schema in TOOL_SCHEMAS.items():
            try:
                ctx.register_tool(tool_name, func=TOOL_HANDLERS[tool_name], schema=tool_schema, is_echo=False, is_stream=False)
                logger.info("Registered tool: %s", tool_name)
            except Exception as e:
                logger.error("Failed to register tool %s: %s", tool_name, e)

        # Register hooks
        for hook_name, hook_func in HOOKS.items():
            if hook_func is not None:
                try:
                    ctx.register_hook(hook_name, hook_func)
                    logger.info("Registered hook: %s", hook_name)
                except Exception as e:
                    logger.error("Failed to register hook %s: %s", hook_name, e)
    else:
        logger.info("seoaeogeo plugin loaded standalone (no Hermes ctx)")

    # NOTE: CLI commands are registered via src/main.py (typer). If Hermes ever
    # exposes a CLI registration API, this is where we would call it. For now,
    # the standalone CLI works independently of Hermes.
