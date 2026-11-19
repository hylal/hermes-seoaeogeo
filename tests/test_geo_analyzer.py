"""Unit tests for hermes-seoaeogeo — GEO analyzer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analyzers.geo_analyzer import GEOAnalyzer


class TestGEOAnalyzer(unittest.TestCase):
    """Tests for LLM citability scoring and E-E-A-T detection."""

    def test_json_ld_detected_increases_score(self):
        html = (
            '<html><body>'
            '<p>In our experience we tested this approach.</p>'
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Article"}'
            '</script>'
            '</body></html>'
        )
        result = GEOAnalyzer().evaluate_llm_citability(html)
        self.assertGreaterEqual(result["citability_score"], 15)
        signals_text = " ".join(result["signals"])
        self.assertIn("Structured data", signals_text)

    def test_e_e_at_experience_signal(self):
        html = '<html><body>' \
               '<p>We used this method in production and it worked great.</p>' \
               '<p>Our personal experience shows results.</p>' \
               '</body></html>'
        result = GEOAnalyzer().evaluate_llm_citability(html)
        self.assertGreaterEqual(result["citability_score"], 20)
        signals_text = " ".join(result["signals"])
        self.assertIn("experience", signals_text.lower())

    def test_quotable_signals_detected(self):
        html = '<html><body>' \
               '<p>The key takeaway is important.</p>' \
               '<p>This is a best practice recommendation.</p>' \
               '<p>Data point: 45% of users prefer this.</p>' \
               '</body></html>'
        result = GEOAnalyzer().evaluate_llm_citability(html)
        self.assertGreaterEqual(result["citability_score"], 10)
        self.assertIn("Quotable signal", " ".join(result["signals"]))

    def test_quantitative_data_increases_score(self):
        html = '<html><body>' \
               '<p>Over 75 percent of companies adopted AI tools.</p>' \
               '<p>The project grew 3 times faster.</p>' \
               '</body></html>'
        result = GEOAnalyzer().evaluate_llm_citability(html)
        signals_text = " ".join(result["signals"])
        self.assertIn("Quantitative data", signals_text)

    def test_recommendations_are_nonempty(self):
        html = "<html><body><p>Some content</p></body></html>"
        result = GEOAnalyzer().evaluate_llm_citability(html)
        self.assertGreater(len(result["recommendations"]), 0)

    def test_score_caps_at_100(self):
        # Feed a very signal-rich HTML to test the cap
        parts = []
        for i in range(20):
            parts.append(f'<p>We recommend this best practice item {i}.</p>')
        parts.append('<script type="application/ld+json">{"@type":"Article"}</script>')
        html = "<html><body>" + "".join(parts) + "</body></html>"
        result = GEOAnalyzer().evaluate_llm_citability(html)
        self.assertLessEqual(result["citability_score"], 100)

    def test_empty_html_returns_low_score(self):
        result = GEOAnalyzer().evaluate_llm_citability("<html><body></body></html>")
        self.assertLessEqual(result["citability_score"], 5)

    def test_properties_accessible(self):
        analyzer = GEOAnalyzer()
        analyzer.evaluate_llm_citability("<html><body><p>Test</p></body></html>")
        self.assertIsInstance(analyzer.score, int)
        self.assertIsInstance(analyzer.signals, list)


if __name__ == "__main__":
    unittest.main()
