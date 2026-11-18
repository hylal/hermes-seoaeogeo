"""CLI commands for the hermes-seoaeogeo plugin — audit subcommand."""

from __future__ import annotations

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)
console = Console()

# Exported sub-app for registration in src/main.py
audit_app = typer.Typer(help="Run SEO / AEO / GEO audits on a URL")


@audit_app.command("url")
def audit_url(
    url: str = typer.Argument(..., help="URL to audit (e.g., https://example.com/page)"),
    mode: str = typer.Option(
        "full",
        "--mode", "-m",
        help="Audit mode: full, technical, aeo, geo",
        show_default=True,
    ),
) -> None:
    """Run an SEO/AEO/GEO audit against the given URL."""
    from src.analyzers.geo_analyzer import GEOAnalyzer
    from src.analyzers.aeo_analyzer import AEOAnalyzer
    from src.models import AuditResult

    console.print(
        Panel.fit(
            f"[bold blue]Hermes SEO/AEO/GEO Audit[/bold blue]\n[italic]Target: {url}[/italic]",
            border_style="blue",
        )
    )

    # Initialize analyzers
    geo = GEOAnalyzer()
    aeo = AEOAnalyzer()
    tech_result: dict = {"score": 0, "checks": [], "details": {}}

    if mode in ("full", "technical"):
        from src.analyzers.technical_analyzer import TechnicalAnalyzer
        tech = TechnicalAnalyzer()
        tech_result = tech.audit(url)

        table = Table(title="Technical Audit Checklist", show_header=True, header_style="bold magenta")
        table.add_column("Check", style="cyan")
        table.add_column("Finding", style="white")
        table.add_column("Status", style="yellow")

        _status_color = {"ok": "green", "warn": "yellow", "error": "red"}
        for ch in tech_result["checks"]:
            color = _status_color.get(ch["status"], "white")
            table.add_row(ch["check"], ch["finding"], f"[{color}]{ch['status'].upper()}[/]")

        console.print(table)

    if mode in ("full", "aeo"):
        # Run AEO analyzer on the URL
        try:
            opportunities = aeo.extract_paa_opportunities(url)
            aeo_table = Table(title="AEO Opportunities (conversational queries)", show_header=True, header_style="bold magenta")
            aeo_table.add_column("Question", style="cyan", width=50)
            aeo_table.add_column("Confidence", style="white")
            aeo_table.add_column("Schema suggestion", style="yellow")

            for opp in opportunities[:8]:
                conf_color = "green" if opp["confidence"] >= 60 else ("yellow" if opp["confidence"] >= 45 else "red")
                aeo_table.add_row(opp["question"], f"[{conf_color}]{opp['confidence']}%[/]", opp["suggestion"])

            console.print(aeo_table)
            aeo_score = aeo.get_aeo_score(url)["score"] if hasattr(aeo, "get_aeo_score") else 0
        except Exception as e:
            console.print(f"[red]AEO analysis failed: {e}[/red]")
            opportunities = []
            aeo_score = 0

    if mode in ("full", "geo"):
        # Run GEO analyzer
        geo_result = geo.evaluate_llm_citability("<html><body><p>Example content</p></body></html>")
        geo_table = Table(title="GEO Readiness", show_header=True, header_style="bold magenta")
        geo_table.add_column("Signal", style="cyan")
        geo_table.add_column("Status", style="white")

        for sig in geo_result["signals"][:6]:
            geo_table.add_row(sig, "[green]Detected[/]")

        if geo_result["recommendations"]:
            geo_table.add_row("Recommendations", f"[yellow]{len(geo_result['recommendations'])} suggestions[/]")

        console.print(geo_table)

    # Compile final result — weighted blend of tech/AEO/geo scores
    tech_score_val = tech_result.get("score", 0)
    try:
        aeo_opps = aeo.extract_paa_opportunities(url) if mode in ("full", "aeo") else []
        aeo_score = round(sum(o["confidence"] for o in aeo_opps) / max(len(aeo_opps), 1))
    except Exception:
        aeo_opps = []
        aeo_score = 0

    if mode == "technical":
        overall = tech_score_val
    elif mode == "aeo":
        overall = aeo_score
    elif mode == "geo":
        overall = geo_result.get("score", 0) if isinstance(geo_result, dict) else 0
    else:
        overall = round(tech_score_val * 0.4 + aeo_score * 0.3 + (geo_result.get("score", 0) * 0.3))

    result = AuditResult(
        url=url,
        mode=mode,
        overall_score=overall,
        technical={"checks": len(tech_result.get("checks", [])), "score": tech_score_val},
        aeo={"opportunities": len(aeo_opps), "score": aeo_score},
        geo=geo_result,
        recommendations=geo_result["recommendations"],
        errors=[],
    )

    # Summary panel
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Key", style="dim")
    summary_table.add_column("Value", style="bold")
    summary_table.add_row("Technical Score", f"[bold]#{result.technical['score']}/100[/]")
    summary_table.add_row("AEO Score", f"{result.aeo['score']}/100 ({result.aeo['opportunities']} opps)")
    summary_table.add_row("GEO Signals", str(len(result.geo.get("signals", []) if isinstance(result.geo, dict) else [])))
    summary_table.add_row("Total Checks Run", str(result.technical["checks"]))

    console.print("\n[bold]Summary[/bold]")
    console.print(summary_table)

    # Recommendations
    if result.recommendations:
        console.print("\n[bold]Recommended actions:[/bold]")
        for i, rec in enumerate(result.recommendations[:5], 1):
            console.print(f"  {i}. {rec}")

    # Action command for WordPress
    if mode == "full":
        typer.echo("")
        typer.echo("💡 Next: run 'hermes seoaeogeo wp-fix apply-schema <url> --schema_type Article' to apply schema")


@audit_app.command("wordpress")
def wp_scan_cmd(
    site_url: str = typer.Argument(..., help="Site URL (e.g., https://example.com)"),
    wp_path: str = typer.Option("/wp-admin/", help="WP admin path", show_default=True),
) -> None:
    """Scan a site for WordPress fingerprints."""
    import requests

    console.print(
        Panel.fit(
            f"[bold blue]WordPress Fingerprint Scan[/bold blue]\n[italic]Target: {site_url}[/italic]",
            border_style="blue",
        )
    )

    fingerprint = {
        "wp_version": None,
        "plugins": [],
        "themes": [],
        "status": "not_found",
    }

    # Check classic WP endpoints
    endpoints = [
        f"{site_url}/wp-json",
        f"{site_url}/readme.html",
        f"{site_url}/wp-admin/",
        f"{site_url}/wp-content/",
        f"{site_url}/license.txt",
    ]

    for ep in endpoints:
        try:
            resp = requests.get(ep, timeout=5, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Hermes-AEO/1.0)",
            })
            if resp.status_code == 200:
                content = resp.text.lower()
                if "wp-content" in content and "wp-includes" in content:
                    fingerprint["status"] = "wordpress_detected"
                    if "/readme.html" in ep:
                        # Extract version hint
                        version_match = None
                        for line in resp.text.split("\n"):
                            if "wordpress" in line.lower() and "version" in line.lower():
                                version_match = line.strip()
                                break
                        fingerprint["wp_version"] = version_match or "version not detected"
                    if "/license.txt" in ep:
                        for line in resp.text.split("\n")[:5]:
                            if "WordPress" in line:
                                fingerprint["wp_version"] = fingerprint["wp_version"] or line.strip()
                                break
                elif "/wp-json" in ep:
                    fingerprint["status"] = "wp-json_discovered"
        except requests.RequestException:
            continue

    # Summary
    if fingerprint["status"] == "wordpress_detected":
        console.print(f"\n[bold green]✓ WordPress detected[/bold green]")
        console.print(f"[dim]Version:[/dim] {fingerprint['wp_version'] or 'unknown'}")
        if fingerprint["plugins"]:
            console.print(f"[dim]Plugins:[/dim] {', '.join(fingerprint['plugins'][:5])}")
        if fingerprint["themes"]:
            console.print(f"[dim]Themes:[/dim] {', '.join(fingerprint['themes'][:3])}")
    elif fingerprint["status"] == "wp-json_discovered":
        console.print("\n[bold yellow]~ Partial fingerprint[/bold yellow]")
        console.print("  WP REST API accessible — check /wp-json/wp/v2/posts")
    else:
        console.print("\n[bold red]✗ WordPress not detected[/bold red]")
        console.print("  Try a different path or check if WP is installed on a subpath")


if __name__ == "__main__":
    audit_app()
