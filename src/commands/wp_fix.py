"""CLI commands for the hermes-seoaeogeo plugin — wp-fix subcommand."""

from __future__ import annotations

import json
import logging

import typer
from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()

wp_app = typer.Typer(help="WordPress schema and content automation commands")


@wp_app.command("apply-schema")
def apply_schema_cmd(
    url: str = typer.Argument(..., help="URL to apply schema to"),
    schema_type: str = typer.Option(
        "Article",
        "--schema_type", "-s",
        help="Schema type: Article, FAQPage, HowTo, LocalBusiness, Product",
        show_default=True,
    ),
    output: str = typer.Option(
        "json",
        "--output", "-o",
        help="Output format: json (JSON-LD) or payload (WP REST API)",
        show_default=True,
    ),
) -> None:
    """Generate and optionally apply JSON-LD structured data.

    This tool does NOT modify your WordPress site automatically. It generates the
    exact code you need to run via WP-CLI or the WP REST API. Review the output,
    then apply it manually or via a headless browser.
    """
    from src.analyzers.geo_analyzer import GEOAnalyzer

    console.print(
        Panel.fit(
            f"[bold blue]JSON-LD Schema Generator[/bold blue]\n[italic]Target: {url}[/italic]\n[italic]Schema: {schema_type}[/italic]",
            border_style="blue",
        )
    )

    # Build schema based on type
    if schema_type == "Article":
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "How to Optimize Your Site for AEO, GEO, and Search Engines",
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
        schema_name = "Article"
    elif schema_type == "FAQPage":
        schema = {
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
        schema_name = "FAQPage"
    elif schema_type == "HowTo":
        schema = {
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
        schema_name = "HowTo"
    elif schema_type == "LocalBusiness":
        schema = {
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
        schema_name = "LocalBusiness"
    elif schema_type == "Product":
        schema = {
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
        schema_name = "Product"
    else:
        schema = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": "Auto-generated schema",
            "description": "Generated by hermes-seoaeogeo",
        }
        schema_name = schema_type

    # Generate outputs
    json_ld = json.dumps(schema, indent=2, ensure_ascii=False)

    # WP-CLI command
    wp_cli = (
        f'wp option update _schema_{schema_type} \"{json_ld}\" '
        f'--porcelain'
    )

    # WP REST API payload
    payload = {
        "title": {"rendered": f"{schema_name} Schema for {url}"},
        "content": {
            "rendered": f"The following JSON-LD structured data has been generated:\n\n```json\n{json_ld}\n```\n\nApply via: {wp_cli}"
        },
        "status": "draft",
    }

    if output == "json":
        console.print(Panel(json_ld, title="JSON-LD Output", border_style="green"))
        console.print("\n[dim]Copy the above JSON-LD and add it to your theme's header.php, a plugin, or via WP-CLI:[/dim]")
        console.print(f"[cyan]{wp_cli}[/cyan]")
    elif output == "payload":
        console.print(Panel(json.dumps(payload, indent=2, ensure_ascii=False), title="WP REST API Payload", border_style="green"))
        console.print("\n[dim]POST a new page to:[/dim]")
        console.print(f"[cyan]{url}/wp-json/wp/v2/posts[/cyan]")
        console.print("with headers:")
        console.print("  Authorization: Basic <base64(plugin_password)>")
        console.print("  Content-Type: application/json")
    else:
        console.print(json_ld)
        console.print(f"\n[dim]WP-CLI: {wp_cli}[/dim]")

    # GEO context
    geo = GEOAnalyzer()
    sample = "<html><body><p>Example content</p></body></html>"
    geo_result = geo.evaluate_llm_citability(sample)
    console.print(f"\n[bold]GEO citability score:[/bold] [cyan]{geo_result['citability_score']}/100[/cyan]")
    console.print("[dim]Signals found:[/dim]")
    for s in geo_result["signals"][:5]:
        console.print(f"  [grey50]• {s}[/grey50]")


if __name__ == "__main__":
    wp_app()
