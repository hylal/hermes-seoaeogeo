"""Unit tests for hermes-seoaeogeo — AEO analyzer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analyzers.aeo_analyzer import AEOAnalyzer


class TestAEOAnalyzer(unittest.TestCase):
    """Tests for conversational query extraction and AEO scoring."""

    def _mock_response(self, html: str):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        return resp

    # ------------------------------------------------------------------ extract_paa_opportunities
    def test_heading_with_question_prefix(self):
        html = '<html><head></head><body>' \
               '<h1>What is AEO?</h1>' \
               '<h2>How does GEO work?</h2>' \
               '<p>Body content</p>' \
               '</body></html>'
        with patch("src.analyzers.aeo_analyzer.requests.get", return_value=self._mock_response(html)):
            result = AEOAnalyzer().extract_paa_opportunities("https://example.com")
            questions = [opp["question"] for opp in result]
            self.assertIn("What is AEO?", questions)
            self.assertIn("How does GEO work?", questions)

    def test_bullet_list_generated_queries(self):
        html = '<html><body>' \
               '<ul>' \
               '<li>Best practices for SEO optimization in 2024</li>' \
               '<li>Guide to structured data implementation</li>' \
               '</ul>' \
               '</body></html>'
        with patch("src.analyzers.aeo_analyzer.requests.get", return_value=self._mock_response(html)):
            result = AEOAnalyzer().extract_paa_opportunities("https://example.com")
            self.assertGreaterEqual(len(result), 1)
            for opp in result:
                self.assertIsInstance(opp["question"], str)
                self.assertIsInstance(opp["confidence"], int)
                self.assertIsInstance(opp["suggestion"], str)

    def test_fetch_failure_returns_error(self):
        with patch("src.analyzers.aeo_analyzer.requests.get", side_effect=requests.exceptions.ConnectionError("fail")):
            result = AEOAnalyzer().extract_paa_opportunities("https://example.com")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["confidence"], 0)

    def test_deduplication(self):
        html = '<html><body>' \
               '<h1>what is seo?</h1>' \
               '<p>Another heading about what is seo here.</p>' \
               '</body></html>'
        with patch("src.analyzers.aeo_analyzer.requests.get", return_value=self._mock_response(html)):
            result = AEOAnalyzer().extract_paa_opportunities("https://example.com")
            questions = [opp["question"].lower() for opp in result]
            count_what_is_seo = sum(1 for q in questions if "what is seo" in q)
            self.assertEqual(count_what_is_seo, 1)

    # ------------------------------------------------------------------ get_aeo_score
    def test_score_with_headings_and_lists(self):
        html = '<html><body>' \
               '<h1>T</h1><h2>S</h2><h3>X</h3>' \
               '<ul><li>A</li><li>B</li><li>C</li><li>D</li><li>E</li></ul>' \
               '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script>' \
               '<p>Best guide for SEO what how</p>' \
               '</body></html>'
        with patch("src.analyzers.aeo_analyzer.requests.get", return_value=self._mock_response(html)):
            score_info = AEOAnalyzer().get_aeo_score("https://example.com")
            self.assertGreaterEqual(score_info["score"], 80)
            self.assertGreaterEqual(len(score_info["signals"]), 4)

    def test_score_empty_page(self):
        html = '<html><body><p>Just a short page</p></body></html>'
        with patch("src.analyzers.aeo_analyzer.requests.get", return_value=self._mock_response(html)):
            score_info = AEOAnalyzer().get_aeo_score("https://example.com")
            self.assertLessEqual(score_info["score"], 30)

    def test_score_fetch_failure_returns_zero(self):
        with patch("src.analyzers.aeo_analyzer.requests.get", side_effect=requests.exceptions.ConnectionError("fail")):
            score_info = AEOAnalyzer().get_aeo_score("https://example.com")
            self.assertEqual(score_info["score"], 0)
            self.assertIn("error", score_info)


if __name__ == "__main__":
    unittest.main()
