"""hermes-seoaedgeo — standalone CLI entry point.

Run as `python -m src.main` or install the package to get the `seoaedgeo` command.

Examples:
    seoaedgeo audit url <url> --mode full
    seoaedgeo aeo extract-paa <url> --limit 15
    seoaedgeo geo citability <url>
    seoaedgeo wp-fix apply-schema <url> --schema_type Article
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure src/ is importable when running from the plugin directory
_plugin_dir = Path(__file__).resolve().parent
_src_dir = _plugin_dir
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import typer

from src.commands.audit import audit_app
from src.commands.aeo import aeo_app
from src.commands.geo import geo_app
from src.commands.wp_fix import wp_app

# Root CLI app
cli = typer.Typer(
    name="seoaedgeo",
    help="Hermes SEO / AEO / GEO audit toolkit — technical SEO, answer engine optimization, "
         "generative engine optimization, and WordPress automation.",
)

# Sub-apps (registered here so they appear under their parent command)
cli.add_typer(audit_app, name="audit", help="Run SEO / AEO / GEO audits on a URL")
cli.add_typer(aeo_app,   name="aeo",    help="AEO / PAA query extraction and Q&A schema suggestions")
cli.add_typer(geo_app,   name="geo",    help="GEO / LLM citability analysis and recommendations")
cli.add_typer(wp_app,    name="wp-fix", help="WordPress schema generation and REST API payloads")


def main() -> None:
    """Entry point for the seoaedgeo CLI."""
    cli()


if __name__ == "__main__":
    main()
