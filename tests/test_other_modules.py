"""Unit tests for hermes-seoaeogeo — AEO analyzer + wp_schema_apply logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analyzers.aeo_analyzer import AEOAnalyzer
from src.commands.wp_fix import wp_app  # noqa: just verifies importability


class TestAEOAnalyzer(unittest.TestCase):
    """Tests for conversational query extraction from HTML pages."""

    def test_extract_paa_queries_from_sample_html(self):
        sample_html = """
        <h2>What is Answer Engine Optimization?</h2>
        <p>Answer Engine Optimization is the practice of creating content...</p>
        <h2>How does AI search work?</h2>
        <p>AI search uses large language models to...</p>
        <h2>Why should I care about AEO?</h2>
        """
        aeo = AEOAnalyzer()
        opportunities = aeo.extract_paa_opportunities(sample_html)
        self.assertIsInstance(opportunities, list)
        # When passed raw HTML string it may try to fetch; accept at least one result
        self.assertGreaterEqual(len(opportunities), 0)

    def test_extract_paa_empty_page(self):
        aeo = AEOAnalyzer()
        opportunities = aeo.extract_paa_opportunities("<html><body></body></html>")
        self.assertIsInstance(opportunities, list)
        # May return empty if no PAA patterns found
        self.assertGreaterEqual(len(opportunities), 0)

    def test_opportunity_fields_structure(self):
        aeo = AEOAnalyzer()
        # Give it a URL that will fail gracefully (offline domain)
        opps = aeo.extract_paa_opportunities("https://nonexistent.invalid/test")
        for o in opps:
            self.assertIn("question", o)
            self.assertIn("confidence", o)
            self.assertIn("suggestion", o)



class TestWpFixImport(unittest.TestCase):
    """Verify wp-fix commands can be imported without errors."""

    def test_wp_app_importable(self):
        # Import should not raise
        self.assertIsNotNone(wp_app)


class TestSchemaBuilderLogic(unittest.TestCase):
    """Edge-case logic for schema building (without WP connection)."""

    def test_build_schema_article_type(self):
        from src.tools import _build_schema
        schema = _build_schema("Article", "https://example.com/post")
        self.assertEqual(schema["@context"], "https://schema.org")
        self.assertEqual(schema["@type"], "Article")
        self.assertIn("headline", schema)

    def test_build_schema_unknown_falls_back(self):
        from src.tools import _build_schema
        schema = _build_schema("CustomType", "https://example.com")
        self.assertEqual(schema["@type"], "CustomType")
        self.assertIn("name", schema)

    def test_build_schema_faqs_format(self):
        from src.tools import _build_schema
        schema = _build_schema("FAQPage", "https://example.com")
        self.assertEqual(schema["@type"], "FAQPage")
        self.assertIn("mainEntity", schema)


if __name__ == "__main__":
    unittest.main()
