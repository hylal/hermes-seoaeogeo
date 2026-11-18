"""CLI hooks — pre_tool_call observer hook for the Hermes plugin.

Observes all tool calls and logs audit activity. This is a simple no-op observer
that just records when the seo_audit or wp_schema_apply tools fire, for logging.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def on_pre_tool_call(tool_name: str, args: dict, task_id: str, **_: any) -> None:
    """Pre-tool-call hook — logs the audit command being executed.

    This hook is registered with Hermes via ctx.register_hook('pre_tool_call', ...).
    It's a lightweight observer — no return value needed.

    Args:
        tool_name: Name of the tool being called.
        args: Arguments passed to the tool.
        task_id: Hermes task/session identifier.
    """
    if tool_name in ("seo_audit", "wp_schema_apply", "get_aeo_opportunities"):
        logger.info(
            "seoaeogeo audit tool called: %s (url=%s)",
            tool_name,
            args.get("url", "unknown"),
            extra={"task_id": task_id},
        )
