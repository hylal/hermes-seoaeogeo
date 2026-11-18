"""CLI commands for the hermes-seoaeogeo plugin — geo subcommand."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

geo_app = typer.Typer(help="GEO-specific commands")


@geo_app.command("citability")
def citability_cmd(
    url: str = typer.Argument(..., help="URL to analyze for LLM citability"),
) -> None:
    """Analyze a page for LLM citability, E-E-A-T signals, and GEO readiness."""
    from src.analyzers.geo_analyzer import GEOAnalyzer

    console.print(
        Panel.fit(
            f"[bold blue]GEO / LLM Citability Analysis[/bold blue]\n[italic]Target: {url}[/italic]",
            border_style="blue",
        )
    )

    analyzer = GEOAnalyzer()

    # Fetch actual page content from the target URL for real GEO analysis
    import requests as _req
    try:
        resp = _req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        from bs4 import BeautifulSoup as _BS
        soup = _BS(resp.text, "html.parser")
        article = soup.find("article") or soup.find("main") or soup
        example_html = str(article)
    except Exception as e:
        logger.warning("Could not fetch %s: %s — falling back to template", url, e)
        example_html = """
    <html><body><article><h1>Citability Test</h1>
    <p>In our experience, optimizing for AI search requires a different approach than traditional SEO.</p>
    <p><strong>Key takeaway:</strong> Add clear author credentials and structured data.</p>
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","headline":"Test","author":{"@type":"Person","name":"Hilaludin Wahid"}}</script>
    </article></body></html>
    """
    result = analyzer.evaluate_llm_citability(example_html)

    # Score panel
    console.print(
        Panel(
            f"[bold]LLM Citability Score: {result['citability_score']}/100[/bold]",
            title="GEO Score",
            border_style="green",
        )
    )

    # Signals table
    if result["signals"]:
        sig_table = Table(title="Detected Signals", show_header=True, header_style="bold magenta")
        sig_table.add_column("Signal", style="cyan")
        sig_table.add_column("Count", style="white")
        for sig in result["signals"][:8]:
            # Extract count from signal
            count = 1
            import re
            match = re.search(r"\((\d+)\)", sig)
            if match:
                count = match.group(1)
            sig_table.add_row(sig, str(count))

        console.print(sig_table)

    # Recommendations
    console.print("\n[bold]GEO Recommendations:[/bold]")
    for i, rec in enumerate(result["recommendations"], 1):
        console.print(f"  {i}. [green]{rec}[/green]")

    # Next step
    console.print("\n[bold]Next:[/bold]")
    console.print("Run 'hermes seoaeogeo wp-fix apply-schema <url> -s Article' to generate schema code")


if __name__ == "__main__":
    geo_app()
