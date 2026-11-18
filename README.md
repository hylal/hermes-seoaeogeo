# hermes-seoaeogeo

**Advanced SEO / AEO / GEO Audit Toolkit for Hermes Agent** — with native WordPress schema automation.

Built by **Hilaludin Wahid** · MIT License · [GitHub](https://github.com/hylal/hermes-seoaeogeo)

---

## What is this?

`hermes-seoaeogeo` is a Hermes Agent plugin that adds three powerful audit tools:

| Tool | Purpose |
|------|---------|
| `seo_audit` | Full technical SEO + AEO + GEO audit of any URL |
| `wp_schema_apply` | Generate JSON-LD schema (Article, FAQPage, HowTo, LocalBusiness, Product) plus WP REST API payload |
| `get_aeo_opportunities` | Extract People-Also-Ask & conversational queries, suggest FAQ/Q&A schema |

### Why it matters

Traditional SEO tools stop at meta tags and page speed. This toolkit also checks **AEO** (is your content answer-engine friendly?) and **GEO** (will LLMs cite your content when they generate search results?). Combined with one-click JSON-LD generation you can paste directly into WordPress, it closes the gap between research and publish.

---

## Installation

```bash
# Clone or link from your local workspace
hermes plugin link . --source C:/Users/Digital-MKT/Documents/hermes-seoaeogeo
```

Or install standalone:

```bash
cd C:/Users/Digital-MKT/Documents/hermes-seoaeogeo
pip install -e .
```

Once linked inside Hermes Agent, the tools appear automatically in your agent's tool roster under the `seoaeogeo` set.

---

## CLI Quick Start

Run directly from the command line (no Hermes required):

```bash
# Full audit
seoaeogeo audit https://domain.co.id/blog/post --mode full

# Technical-only audit
seoaeogeo audit https://example.com --mode technical

# AEO PAA extraction
seoaeogeo aeo extract-paa https://example.com/blog --limit 15

# GEO citability analysis
seoaeogeo geo citability https://example.com/article

# WordPress schema generator
seoaeogeo wp-fix apply-schema https://example.com/product --schema_type Article --output json
```

---

## Tools Reference

### `seo_audit`

Audit a URL across three dimensions simultaneously. Returns a structured JSON result with score, signals, and actionable recommendations.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | ✅ | Page URL to audit |
| `mode` | enum | ❌ | `full` (default), `technical`, `aeo`, `geo` |

**Returns:** JSON object with `overall_score`, `technical`, `aeo`, `geo`, `recommendations`, `errors`.

---

### `wp_schema_apply`

Generate valid JSON-LD structured data and a WP REST API draft post for the selected schema type. The generated code is ready to copy/paste into a WordPress block, theme template, or WP-CLI command.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | ✅ | Target page URL |
| `schema_type` | enum | ❌ | `Article` (default), `FAQPage`, `HowTo`, `LocalBusiness`, `Product` |
| `output` | enum | ❌ | `json` (JSON-LD snippet, default) or `payload` (WP REST API POST body) |

**Returns:** JSON with `schema`, `json_ld`, `wp_cli`, and `payload` keys.

---

### `get_aeo_opportunities`

Extract People-Also-Ask questions and conversational query patterns from a URL using pattern matching against headings, lists, and intent keywords. Returns Q&A opportunities ranked by confidence with suggested schema types.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | ✅ | Page URL to scan |
| `limit` | int | ❌ | Max opportunities to return (default 10) |

**Returns:** JSON with `score`, `opportunities` list (each has `question`, `confidence`, `type`, `suggestion`), and `recommendations`.

---

## Hooks

### `pre_tool_call`

Observed via the Hermes hook system. Fires before every `seo_audit`, `wp_schema_apply`, or `get_aeo_opportunities` call. Useful for logging audit history to an external system or integrating with other plugins.

---

## Architecture

```
hermes-seoaeogeo/
├── src/                          # Core Python package (runnable standalone)
│   ├── main.py                   # Typer root CLI entry point
│   ├── schemas.py                # Tool schemas (what the agent reads)
│   ├── tools.py                  # Tool handlers (the actual logic)
│   ├── _registry.py              # Plugin registration hub
│   ├── cli_hooks.py              # pre_tool_call hook observer
│   ├── models.py                 # Pydantic data models
│   ├── commands/                 # CLI subcommands (audit, aeo, geo, wp-fix)
│   │   ├── audit.py
│   │   ├── aeo.py
│   │   ├── geo.py
│   │   └── wp_fix.py
│   └── analyzers/                # Domain analyzers
│       ├── aeo_analyzer.py       # Conversational query extraction
│       └── geo_analyzer.py       # LLM citability scoring
├── hermes_seoaeogeo/             # Hermes plugin package
│   └── __init__.py               # Entry point (register function)
├── tests/                        # Test suite skeleton
├── plugin.yaml                   # Hermes manifest
├── pyproject.toml                # Package config & dependencies
└── README.md
```

---

## Dependencies

| Package | Version | Use |
|---------|---------|-----|
| `typer` | `>=0.9,<1.0` | CLI framework |
| `rich` | `>=13.0,<14.0` | Terminal output (tables, panels, colored text) |
| `pydantic` | `>=2.0,<3.0` | Data validation for audit results |
| `requests` | `>=2.28,<3.0` | HTTP fetching (pages & endpoints) |
| `beautifulsoup4` | `>=4.12,<5.0` | HTML parsing for analyzers |
| `httpx` | `>=0.27,<1.0` | Async HTTP (future use) |

Python requirement: **3.11+**.

---

## Planned Improvements (v1.1+)

- [ ] DataForSEO API integration for real SERP feature detection
- [ ] Live WordPress REST API submission (with API key auth)
- [ ] Bulk audit mode (scan an entire sitemap)
- [ ] Chrome DevTools Protocol (CDP) support for JS-rendered pages
- [ ] Output formats: CSV, Markdown report

---

## License

MIT License. See [LICENSE](LICENSE) for details.
