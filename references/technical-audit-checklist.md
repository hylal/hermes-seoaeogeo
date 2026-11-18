# Technical Audit Checklist

Full on-page SEO checklist evaluated by `TechnicalAnalyzer.audit()`.

## Checklist Items

| # | Check | Status | Weight |
|---|-------|--------|--------|
| 1 | Protocol (HTTPS enabled) | ok / error | 10 |
| 2 | HTTP Status (200 OK) | ok / warn / error | 10 |
| 3 | Title tag present, 30–60 chars | ok / warn / error | 10 |
| 4 | Meta description present, 120–160 chars | ok / warn / error | 10 |
| 5 | Exactly one H1 tag | ok / warn / error | 10 |
| 6 | Headings hierarchy (H2–H6 present) | ok / warn | 5 |
| 7 | Image alt attributes (>90% tagged) | ok / warn / error | 10 |
| 8 | Canonical link present | ok / warn | 5 |
| 9 | Open Graph tags (4 core present) | ok / warn | 5 |
| 10 | Structured data (JSON-LD or Microdata) | ok / warn | 10 |
| 11 | Robots meta (no index / follow, or no robots) | ok / warn / error | 5 |
| 12 | Content length > 300 words | ok / warn / error | 3 |
| 13 | Link balance (internal + external) | ok / warn | 2 |

## Scoring Formula

```
score = (earned / total_weight) * 100
```

Where:
- `ok` → 1.0× weight
- `warn` → 0.5× weight
- `error` → 0.0× weight

## Target Signals

| Signal | Target | Note |
|--------|--------|------|
| HTTPS | `https://` in final URL | Redirect HTTP → HTTPS recommended |
| Title | 30–60 characters | Longer titles get truncated in SERP |
| Meta description | 120–160 characters | Important for CTR; keep under 160 |
| H1 | Exactly 1 | Multiple H1s confuse screen readers and SEO |
| Image alt | >90% of images tagged | Use descriptive, keyword-relevant alt text |
| Canonical | Absolute URL (https://...) | Relative canonicals cause duplicate content |
| JSON-LD | At least 1 structured data block | Article, Organization, Product, FAQPage |
| Word count | >300 words | Thin content ranks poorly; 500+ recommended |
| Open Graph | 4 tags (og:title, og:description, og:image, og:url) | Required for social sharing cards |

## Common Failures

| Failure | Fix |
|---------|-----|
| H1 missing | Add a single H1 containing the primary keyword |
| Title too short | Add the target keyword or brand name |
| No meta description | Write a 120–160 char summary of the page content |
| No canonical | Add `<link rel="canonical" href="https://...">` to head |
| No JSON-LD | Add JSON-LD structured data in `<script type="application/ld+json">` |
| No OG tags | Add Open Graph meta tags for social sharing |
| HTTP not HTTPS | Configure SSL certificate (Let's Encrypt or paid CA) |
