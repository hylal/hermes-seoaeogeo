"""GEO (Generative Engine Optimization) analyzer — LLM citability and AI readiness."""

from __future__ import annotations

import re
from typing import Any

# E-E-A-T signals we look for in text
E_E_A_T_PATTERNS = {
    "experience": [
        r"\b(I|we)\b.*\b(use|tested|tried|worked)\b",
        r"\b(live|in production|on our site)\b",
        r"\b(personal experience|real-world)\b",
    ],
    "expertise": [
        r"\b(expert|specialist|engineer|developer)\b",
        r"\b(certifications?|trained|certified)\b",
        r"\b\d{4,4}\b",  # year references
    ],
    "authoritativeness": [
        r"\b(authoritative|industry leader|trusted)\b",
        r"\b(backlink|reference|peer-reviewed)\b",
        r"\b(generator|reference)\b",
    ],
    "trustworthiness": [
        r"\b(trust|verified|accurate)\b",
        r"\b(disclaimer|privacy policy|terms)\b",
        r"\b(contact us|about us|support)\b",
    ],
}

# Signals that make content more citable / quotable by AI
QUOTABLE_SIGNALS = [
    "clear statement",
    "definition",
    "key takeaway",
    "summary",
    "recommendation",
    "best practice",
    "data point",
    "stat",
    "result",
    "advantage",
]

# Boilerplate text to strip before analysis
BOILERPLATE_PATTERNS = [
    r"copyright.*",
    r"privacy policy",
    r"terms of service",
    r"all rights reserved",
    r"cookie policy",
]


class GEOAnalyzer:
    """Evaluate content for LLM citability and GEO readiness.

    Produces a citability score plus actionable recommendations for improving
    how AI/LLM systems cite and present the content.
    """

    def __init__(self) -> None:
        self._score = 0
        self._signals = []

    def evaluate_llm_citability(self, html_content: str) -> dict[str, Any]:
        """Analyze HTML content for E-E-A-T signals and structured data.

        Args:
            html_content: Raw HTML string to analyze.

        Returns:
            Dict with citability_score (0-100), signals list, and recommendations.
        """
        # Strip boilerplate and script/styles
        text = self._strip_html(html_content)

        # Run E-E-A-T pattern matching
        self._score = 0
        self._signals = []
        for category, patterns in E_E_A_T_PATTERNS.items():
            for pat in patterns:
                matches = re.findall(pat, text, re.IGNORECASE)
                if matches:
                    self._score += 10
                    self._signals.append(f" {category}: {len(matches)} match(es)")

        # Check for structured data presence (JSON-LD)
        if "<script type=\"application/ld+json\">" in html_content:
            self._score += 15
            self._signals.append("Structured data: JSON-LD blocks detected")

        # Check for clear quotable signals
        for signal in QUOTABLE_SIGNALS:
            if signal in text.lower():
                self._score += 3
                self._signals.append(f"Quotable signal: {signal}")

        # Check for original data / statistics
        if re.search(r"\d+(\.\d+)?\s*(%|times|folds|percent)", text):
            self._score += 5
            self._signals.append("Quantitative data present")

        # Constraint: score cap at 100
        self._score = min(100, self._score)

        # Build recommendations
        recommendations = self._build_recommendations()

        return {
            "citability_score": self._score,
            "signals": self._signals,
            "recommendations": recommendations,
        }

    def _strip_html(self, html: str) -> str:
        """Remove scripts, styles, and boilerplate, then extract text."""
        # Remove <script> and <style> content
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Extract visible text
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)

        # Remove boilerplate
        for pat in BOILERPLATE_PATTERNS:
            text = re.sub(pat, "", text, flags=re.IGNORECASE)

        return text.strip()

    def _build_recommendations(self) -> list[str]:
        """Generate actionable GEO recommendations."""
        recs = [
            "Add clear author byline with credentials or role",
            "Include a published/updated date and author contact info",
            "Add JSON-LD schema (Article, FAQPage, or HowTo) with author fields",
            "Write 3-5 clear 'key takeaway' sentences using quotable signals",
            "Include original data, stats, or benchmarks with sources",
            "Add a brief executive summary at the top of the article",
            "Use 'In our experience' or 'We tested' phrases for experience signals",
            "Add comparison tables for 'how-to' and 'vs' content",
            "Include external citations with links to authoritative sources",
            "Add a clear 'what you'll learn' or 'key takeaways' section",
        ]
        return recs

    @property
    def score(self) -> int:
        """Current citability score."""
        return self._score

    @property
    def signals(self) -> list[str]:
        """List of detected signals."""
        return self._signals
