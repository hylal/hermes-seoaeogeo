"""CLI commands for the hermes-seoaeogeo plugin — aeo subcommand."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

aeo_app = typer.Typer(help="AEO-specific commands")


@aeo_app.command("extract-paa")
def extract_paa_cmd(
    url: str = typer.Argument(..., help="URL to analyze for PAA opportunities"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results to show"),
) -> None:
    """Extract People Also Ask (PAA) opportunities and suggest Q&A schema."""
    from src.analyzers.aeo_analyzer import AEOAnalyzer

    console.print(
        Panel.fit(
            f"[bold blue]AEO / PAA Opportunity Extractor[/bold blue]\n[italic]Target: {url}[/italic]",
            border_style="blue",
        )
    )

    analyzer = AEOAnalyzer()
    opportunities = analyzer.extract_paa_opportunities(url)

    if not opportunities:
        console.print("\n[bold yellow]No PAA opportunities found.[/bold yellow]")
        console.print("Try a different URL or add more content to the page.")
        return

    # Group by type
    question_table = Table(title="Top PAA Questions", show_header=True, header_style="bold magenta")
    question_table.add_column("Question", style="cyan", width=60)
    question_table.add_column("Confidence", style="cyan")
    question_table.add_column("Schema", style="cyan")

    for opp in opportunities[:limit]:
        conf_color = "green" if opp["confidence"] >= 60 else ("yellow" if opp["confidence"] >= 45 else "red")
        schema_type = "FAQPage" if opp["type"] == "FAQPage" else "QAPage"
        question_table.add_row(
            opp["question"],
            f"[{conf_color}]{opp['confidence']}%[/]",
            schema_type,
        )

    console.print(question_table)

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"[green]• Detected[/green] [cyan]{len(opportunities)}[/cyan] opportunities (showing top {limit})")
    console.print(f"[yellow]• Avg confidence:[/yellow] {sum(o['confidence'] for o in opportunities) / max(1, len(opportunities)):.0f}%")
    console.print("[dim]• Use these questions as FAQPage or QAPage schema candidates[/dim]")

    # Suggest schema
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Add a FAQPage schema to your site with these questions")
    console.print("2. Write 40-60 word answers for each question")
    console.print("3. Test with the Rich Snippet Test tool in Google Search Console")


if __name__ == "__main__":
    aeo_app()
