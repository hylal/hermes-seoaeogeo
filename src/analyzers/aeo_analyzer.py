"""AEO (Answer Engine Optimization) analyzer — conversational query and snippet detection."""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, List, Tuple

import requests
from bs4 import BeautifulSoup

# Common question prefixes that signal conversational queries
QUESTION_PREFIXES = [
    "what", "why", "how", "when", "where", "who", "which", "is", "are", "can", "could",
    "should", "would", "best", "easy", "fast", "cheap", "top", "guide", "review",
]

# Semantic keywords that often indicate intent to answer a question
INTENT_KEYWORDS = ["what", "how", "why", "best", "guide", "review", "vs", "compare", "advantages"]


class AEOAnalyzer:
    """Extract conversational queries and recommend Q&A schema for featured snippets.

    Featuring a fast local heuristic pipeline — no network call needed. Use the real
    DataForSEO API by passing ``api_key`` and setting ``use_api=True`` for production.
    """

    def __init__(self, api_key: str | None = None, use_api: bool = False) -> None:
        self.api_key = api_key
        self.use_api = use_api

    def extract_paa_opportunities(self, url: str) -> List[dict[str, Any]]:
        """Identify conversational queries and suggest Q&A schema additions.

        Args:
            url: Page URL to analyze.

        Returns:
            List of opportunity dicts with question, confidence, and suggested schema.
        """
        soup = self._fetch_soup(url)
        if soup is None:
            return [{"query": url, "confidence": 0, "question": "Unable to fetch page", "suggestion": "Fix network / block status"}]

        # Combined text content for analysis
        text = soup.get_text(" ", strip=True)
        text_lower = text.lower()

        # Extract H1-H6 headings (often map to queries)
        headings = [h.get_text(" ", strip=True) for h in soup.find_all(re.compile(r"^h[1-6]$"))]
        headings = [h for h in headings if len(h) > 10]

        # Extract bullet/numbered lists (often contain Q&A pairs)
        bullets = [li.get_text(" ", strip=True) for li in soup.find_all(["li", "dt", "td"])]
        bullets = [b for b in bullets if len(b) > 20 and len(b) < 500]

        opportunities = []

        # Heuristic 1: from headings
        for h in headings[:15]:
            q = self._normalize_query(h)
            if q:
                opportunities.append(self._make_opp(
                    question=q, confidence=60,
                    suggestion="Use <Question> in FAQPage or HowTo schema",
                    source="heading",
                ))

        # Heuristic 2: from bullet lists
        for b in bullets[:15]:
            q = self._normalize_query(b)
            if q:
                opportunities.append(self._make_opp(
                    question=q, confidence=50,
                    suggestion="Add <Question> element to FAQPage schema",
                    source="bullet",
                ))

        # Heuristic 3: keyword-driven question generation
        for kw in INTENT_KEYWORDS:
            if kw in text_lower:
                q = self._generate_question(kw)
                opportunities.append(self._make_opp(
                    question=q, confidence=45,
                    suggestion="Structure as FAQPage with <Question>-<Answer> pairs",
                    source="keyword",
                ))

        # Deduplicate
        seen = set()
        unique = []
        for opp in opportunities:
            key = opp["question"].lower()
            if key not in seen:
                seen.add(key)
                unique.append(opp)

        return unique[:20]

    def _fetch_soup(self, url: str) -> BeautifulSoup | None:
        """Fetch and parse HTML, returning a BeautifulSoup object or None."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Hermes-AEO/1.0; +https://myleben.co.id)",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException:
            return None

    def _normalize_query(self, text: str) -> str:
        """Convert a statement into a natural question form."""
        t = text.strip()
        # Remove common trailing punctuation
        t = re.sub(r"[.\!\?]+$", "", t)
        for prefix in QUESTION_PREFIXES:
            if t.lower().startswith(prefix):
                # Add question mark if no punctuation
                if not t.endswith("?"):
                    t += "?"
                return t
        # If it's already a question, return as-is
        if "?" in t:
            return t
        # No clear question — skip
        return ""

    def _generate_question(self, keyword: str) -> str:
        """Generate a natural question from an intent keyword."""
        templates = [
            f"What is {keyword}?",
            f"How does {keyword} work?",
            f"Why is {keyword} important?",
            f"What are the benefits of {keyword}?",
            f"How to {keyword} effectively?",
        ]
        return templates[len(keyword) % len(templates)]

    def _make_opp(self, question: str, confidence: int, suggestion: str, source: str) -> dict[str, Any]:
        """Build a standardized opportunity dict."""
        return {
            "question": question,
            "confidence": confidence,
            "suggestion": suggestion,
            "source": source,
            "type": "QAPage" if confidence >= 60 else "FAQPage",
        }

    def get_aeo_score(self, url: str) -> dict[str, Any]:
        """Compute an AEO readiness score from a page.

        Returns:
            Dict with score (0-100), signals, and breakdown.
        """
        soup = self._fetch_soup(url)
        if soup is None:
            return {"score": 0, "signals": [], "breakdown": {}, "error": "Could not fetch page"}

        text = soup.get_text(" ", strip=True)
        # Check for FAQ-like structure
        faq_items = soup.find_all("faq")
        # Check for headings
        headings_count = len(soup.find_all(re.compile(r"^h[1-6]$")))
        # Check for lists
        list_items = len(soup.find_all("li"))
        # Check for structured data
        structured = soup.find_all("script", type="application/ld+json")

        # Score heuristic
        score = 0
        signals = []

        if headings_count >= 3:
            score += 20
            signals.append(f"Headings: {headings_count}")
        if list_items >= 5:
            score += 15
            signals.append(f"Lists: {list_items}")
        if structured:
            score += 30
            signals.append(f"Structured data blocks: {len(structured)}")
        if any(p in text.lower() for p in ["what", "how", "why", "best", "guide"]):
            score += 20
            signals.append("Conversational intent detected")
        if faq_items or text.lower().count("?") >= 3:
            score += 15
            signals.append("Q&A patterns present")

        # Cap at 100
        score = min(100, score)

        return {
            "score": score,
            "signals": signals,
            "breakdown": {
                "headings": headings_count,
                "list_items": list_items,
                "structured_data": len(structured),
                "faq_items": len(faq_items),
                "question_marks": text.lower().count("?"),
            },
        }
