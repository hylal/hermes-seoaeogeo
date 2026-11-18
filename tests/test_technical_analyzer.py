"""Unit tests for hermes-seoaeogeo — technical analyzer."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analyzers.technical_analyzer import TechnicalAnalyzer


class TestTechnicalAnalyzer(unittest.TestCase):
    """Tests for real technical SEO analysis."""

    def _make_soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    # ------------------------------------------------------------------ protocol
    def test_https_url_is_ok(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com/page"
            mock_resp.status_code = 200
            mock_resp.text = '<html><head><title>Test</title></head><body></body></html>'
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com/page")
            protocols = [c for c in result["checks"] if c["check"] == "Protocol"]
            self.assertEqual(len(protocols), 1)
            self.assertEqual(protocols[0]["status"], "ok")

    def test_http_url_is_error(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "http://example.com/page"
            mock_resp.status_code = 200
            mock_resp.text = '<html><head><title>Test</title></head><body></body></html>'
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("http://example.com/page")
            protocols = [c for c in result["checks"] if c["check"] == "Protocol"]
            self.assertEqual(len(protocols), 1)
            self.assertEqual(protocols[0]["status"], "error")

    # ------------------------------------------------------------------ title
    def test_missing_title_tag(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = "<html><body>No title here</body></html>"
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            titles = [c for c in result["checks"] if c["check"] == "Title Tag"]
            self.assertEqual(titles[0]["status"], "error")

    def test_short_title_warns(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = '<html><head><title>Hi</title></head><body></body></html>'
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            titles = [c for c in result["checks"] if c["check"] == "Title Tag"]
            self.assertEqual(titles[0]["status"], "warn")

    def test_optimal_title_passes(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = '<html><head><title>This is a good title between thirty and sixty chars</title></head><body></body></html>'
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            titles = [c for c in result["checks"] if c["check"] == "Title Tag"]
            self.assertEqual(titles[0]["status"], "ok")

    # ------------------------------------------------------------------ h1
    def test_single_h1_ok(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = '<html><head></head><body><h1>Hello</h1><p>Body</p></body></html>'
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            h1_checks = [c for c in result["checks"] if c["check"] == "H1 Count"]
            self.assertEqual(h1_checks[0]["status"], "ok")

    def test_no_h1_is_error(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = '<html><head></head><body><p>No heading at all</p></body></html>'
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            h1_checks = [c for c in result["checks"] if c["check"] == "H1 Count"]
            self.assertEqual(h1_checks[0]["status"], "error")

    # ------------------------------------------------------------------ images
    def test_images_with_mixed_alts(self):
        imgs = ' '.join([f'<img src="a{i}.jpg"> <img src="b{i}.jpg" alt="desc">' for i in range(5)])
        html = f'<html><body>{imgs}</body></html>'

        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = html
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            img_checks = [c for c in result["checks"] if c["check"] == "Image Alt"]
            self.assertEqual(img_checks[0]["status"], "warn")

    def test_all_images_have_alt(self):
        imgs = ' '.join([f'<img src="i{j}.jpg" alt="Alt for image {j}">' for j in range(3)])
        html = f'<html><body>{imgs}</body></html>'

        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = html
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            img_checks = [c for c in result["checks"] if c["check"] == "Image Alt"]
            self.assertEqual(img_checks[0]["status"], "ok")

    # ------------------------------------------------------------------ structured data
    def test_json_ld_detected(self):
        ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": "Test"})
        html = f'<script type="application/ld+json">{ld}</script>'

        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = html
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            sd_checks = [c for c in result["checks"] if c["check"] == "Structured Data"]
            self.assertEqual(sd_checks[0]["status"], "ok")
            self.assertEqual(result["details"]["structured_data_ld"], 1)

    def test_no_structured_data_warns(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = "<html><body>No schema here</body></html>"
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            sd_checks = [c for c in result["checks"] if c["check"] == "Structured Data"]
            self.assertEqual(sd_checks[0]["status"], "warn")

    # ------------------------------------------------------------------ robots
    def test_noindex_detected_as_error(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = '<meta name="robots" content="noindex, nofollow">'
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            rb = [c for c in result["checks"] if c["check"] == "Robots Meta"]
            self.assertEqual(rb[0]["status"], "error")

    # ------------------------------------------------------------------ overall score
    def test_score_range(self):
        with patch("src.analyzers.technical_analyzer.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com"
            mock_resp.status_code = 200
            mock_resp.text = '''
            <html>
            <head>
                <title>A decent title for our page</title>
                <meta name="description" content="This is a good description of the content on this page.">
                <link rel="canonical" href="https://example.com/decent-page">
            </head>
            <body>
                <h1>Main Heading</h1>
                <h2>Subsection</h2>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
                <img src="photo.jpg" alt="A descriptive photo caption">
                <a href="/other">Link</a>
            </body>
            </html>
            '''.strip()
            mock_get.return_value = mock_resp

            result = TechnicalAnalyzer().audit("https://example.com")
            score = result["score"]
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)
            self.assertIsInstance(score, int)

    def test_fetch_failure_returns_zero(self):
        import requests as req_mod
        # Mock requests.get to directly return None (fetch failure) without raising
        with patch("src.analyzers.technical_analyzer._safe_get", return_value=None):
            result = TechnicalAnalyzer().audit("https://nonexistent.example.invalid")
            self.assertEqual(result["score"], 0)
            self.assertTrue(any(c["status"] == "error" for c in result["checks"]))


if __name__ == "__main__":
    unittest.main()
