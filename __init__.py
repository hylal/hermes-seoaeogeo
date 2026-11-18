"""hermes-seoaeogeo — Advanced SEO, AEO, and GEO audit toolkit."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure src/ is importable regardless of how the plugin is loaded
_plugin_dir = Path(__file__).resolve().parent
_src_dir = _plugin_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))


def register(ctx: object) -> None:
    """Register all tools, hooks, and CLI commands for this plugin."""
    try:
        from src.schemas import (
            SEOAUDIT_SCHEMA,
            WPSCHEMA_SCHEMA,
            AEOPPA_SCHEMA,
        )
        from src.tools import (
            seo_audit_handler,
            wp_schema_apply_handler,
            get_aeo_opportunities_handler,
        )
        from src.cli_hooks import on_pre_tool_call
    except ImportError as exc:
        logger.warning(
            "hermes-seoaeogeo: could not import src modules — "
            "plugin tools will be unavailable. Check installation: %s",
            exc,
        )
        return

    # Register Hermes tools
    ctx.register_tool(
        name="seo_audit",
        toolset="seoaeogeo",
        schema=SEOAUDIT_SCHEMA,
        handler=seo_audit_handler,
    )

    ctx.register_tool(
        name="wp_schema_apply",
        toolset="seoaeogeo",
        schema=WPSCHEMA_SCHEMA,
        handler=wp_schema_apply_handler,
    )

    ctx.register_tool(
        name="get_aeo_opportunities",
        toolset="seoaeogeo",
        schema=AEOPPA_SCHEMA,
        handler=get_aeo_opportunities_handler,
    )

    # Register hook — pre_tool_call observer for audit logging
    ctx.register_hook("pre_tool_call", on_pre_tool_call)

    logger.info(
        "hermes-seoaeogeo: registered 3 tools + 1 hook "
        "(seo_audit, wp_schema_apply, get_aeo_opportunities, pre_tool_call)"
    )

    logger.info("hermes-seoaeogeo plugin registered successfully")
