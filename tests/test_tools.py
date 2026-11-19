"""Unit tests for hermes-seoaeogeo — tool handlers."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.tools import _build_schema, _extract_metadata_from_html, seo_audit_handler


class TestBuildSchema(unittest.TestCase):
    """Tests for dynamic schema building."""

    def test_article_with_default_metadata(self):
        schema = _build_schema("Article", "https://example.com")
        self.assertEqual(schema["@type"], "Article")
        self.assertEqual(schema["@context"], "https://schema.org")
        # Should use defaults when no metadata provided
        self.assertEqual(schema["headline"], "How to Optimize Your Site for AEO, GEO, and Search")

    def test_article_with_live_metadata(self):
        meta = {
            "title": "My Real Article Title",
            "description": "A real description.",
            "author_name": "Jane Doe",
            "author_url": "https://jane.com",
            "image": "https://example.com/img.jpg",
            "date": "2026-01-15",
        }
        schema = _build_schema("Article", "https://example.com", metadata=meta)
        self.assertEqual(schema["headline"], "My Real Article Title")
        self.assertEqual(schema["description"], "A real description.")
        self.assertEqual(schema["author"]["name"], "Jane Doe")
        self.assertEqual(schema["image"], "https://example.com/img.jpg")
        self.assertEqual(schema["datePublished"], "2026-01-15")

    def test_article_fallback_with_partial_metadata(self):
        # Only title provided; rest keeps defaults
        schema = _build_schema("Article", "https://example.com", metadata={"title": "Only Title"})
        self.assertEqual(schema["headline"], "Only Title")
        # description should still be default
        self.assertIsNotNone(schema["description"])

    def test_faqpage_structure(self):
        schema = _build_schema("FAQPage", "https://example.com")
        self.assertEqual(schema["@type"], "FAQPage")
        self.assertEqual(len(schema["mainEntity"]), 2)
        self.assertEqual(schema["mainEntity"][0]["@type"], "Question")

    def test_product_with_metadata_image(self):
        meta = {"image": "https://cdn.example.com/product.jpg"}
        schema = _build_schema("Product", "https://example.com", metadata=meta)
        self.assertEqual(schema["image"], "https://cdn.example.com/product.jpg")

    def test_unknown_type_fallback(self):
        schema = _build_schema("Event", "https://example.com")
        self.assertEqual(schema["@type"], "Event")
        self.assertIsNotNone(schema["name"])

    def test_none_metadata_no_crash(self):
        schema = _build_schema("Article", "https://example.com", metadata=None)
        self.assertEqual(schema["@type"], "Article")


class TestExtractMetadataFromHtml(unittest.TestCase):
    """Tests for metadata extraction from raw HTML."""

    def test_extract_title(self):
        html = "<html><head><title>My Page Title</title></head><body></body></html>"
        result = _extract_metadata_from_html(html, "https://example.com")
        self.assertEqual(result["title"], "My Page Title")

    def test_extract_meta_description(self):
        html = ('<html><head>'
                '<meta name="description" content="This is my description." />'
                '</head><body></body></html>')
        result = _extract_metadata_from_html(html, "https://example.com")
        self.assertEqual(result["description"], "This is my description.")

    def test_extract_og_image(self):
        html = '<html><head><meta property="og:image" content="https://example.com/og.jpg" /></head><body></body></html>'
        result = _extract_metadata_from_html(html, "https://example.com")
        self.assertEqual(result["image"], "https://example.com/og.jpg")

    def test_extract_author_from_jsonld(self):
        ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Article",
            "author": {"@type": "Person", "name": "John Writer", "url": "https://john.com"},
            "datePublished": "2026-03-01T10:00:00Z",
            "image": "https://example.com/photo.jpg",
        })
        html = f'<html><head><script type="application/ld+json">{ld}</script></head><body></body></html>'
        result = _extract_metadata_from_html(html, "https://example.com")
        self.assertEqual(result["author_name"], "John Writer")
        self.assertEqual(result["author_url"], "https://john.com")
        self.assertEqual(result["date"], "2026-03-01")
        self.assertEqual(result["image"], "https://example.com/photo.jpg")

    def test_extract_author_as_list(self):
        ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Article",
            "author": [{"@type": "Person", "name": "Team Author"}],
        })
        html = f'<html><head><script type="application/ld+json">{ld}</script></head><body></body></html>'
        result = _extract_metadata_from_html(html, "https://example.com")
        self.assertEqual(result["author_name"], "Team Author")

    def test_empty_when_no_metadata(self):
        result = _extract_metadata_from_html("<html><body>No meta here</body></html>", "https://example.com")
        self.assertEqual(result["title"], "")
        self.assertEqual(result["description"], "")


class TestSeoAuditHandler(unittest.TestCase):
    """Tests for the seo_audit tool handler."""

    def test_missing_url_returns_error(self):
        result = seo_audit_handler({"mode": "full"})
        parsed = json.loads(result)
        self.assertIn("error", parsed)
        self.assertEqual(parsed["error"], "url is required")

    def test_invalid_mode_defaults_to_full(self):
        # Invalid mode falls through all conditional blocks; scores stay 0
        result = seo_audit_handler({"url": "https://example.com", "mode": "unknown"})
        parsed = json.loads(result)
        self.assertIn("overall_score", parsed)
        self.assertIn("url", parsed)


if __name__ == "__main__":
    unittest.main()
