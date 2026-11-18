"""hermes-seoaedgeo — advanced SEO, AEO, and GEO audit toolkit for Hermes Agent."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register(ctx=None):
    """Plugin entry point registered with Hermes via the hermes_agent.plugins entry point.

    Lazy-loads all tool/handler modules so the plugin works standalone too.
    """
    from src._registry import register as _register_all

    try:
        _register_all(ctx)
        logger.info("hermes-seoaedgeo plugin loaded successfully")
    except Exception as e:
        logger.warning("hermes-seoaedgeo could not load: %s", e)
