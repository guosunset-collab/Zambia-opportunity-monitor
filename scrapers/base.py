import re
import time
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse

from parsers.html_parser import extract_text_and_links


class SourceScraper:
    source_name = "Generic Source"
    source_platform = "Website"
    source_group = "Other"
    ppp_flag = False
    newspaper_flag = False
    social_signal_flag = False
    donor_funded_flag = False

    REQUIRED_OPPORTUNITY_TERMS = [
        "tender",
        "invitation for bids",
        "eoi",
        "expression of interest",
        "rfp",
        "rfq",
        "procurement notice",
        "deadline",
        "closing date",
        "consultancy services",
        "works contract",
        "prequalification",
    ]

    EXCLUDED_TERMS = [
        "homepage",
        "about us",
        "contact",
        "training",
        "public procurement act",
        "airport services",
        "currency notice",
        "currency notices",
        "toll payment notice",
        "toll payment notices",
        "general notice",
        "general notices",
    ]

    def __init__(self, source_config: Dict, run_config: Dict, logger):
        self.source_config = source_config or {}
        self.run_config = run_config or {}
        self.logger = logger
        self.urls = self.source_config.get("urls", [])
        self.timeout = int(self.run_config.get("request_timeout_seconds", 20))
        self.retries = int(self.run_config.get("retries", 2))
        self.max_items = int(self.run_config.get("max_items_per_source", 25))
        self.user_agent = self.run_config.get("user_agent", "Zambia-Infrastructure-Opportunity-Monitor/0.1")

    def scrape(self) -> List[Dict]:
        results: List[Dict] = []
        for url in self.urls:
            try:
                html = self.fetch(url)
                text, links = extract_text_and_links(html, url)
                results.extend(self.extract_from_page(url, text, links))
            except Exception as exc:
                self.logger.warning(
                    f"Source failed gracefully: {self.source_name}",
                    extra={"extra_fields": {"source": self.source_name, "url": url, "error": str(exc)}},
                )
        return results[: self.max_items]

    def fetch(self, url: str) -> str:
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                try:
                    import requests

                    response = requests.get(
                        url,
                        timeout=self.timeout,
                        headers={"User-Agent": self.user_agent},
                    )
                    response.raise_for_status()
                    return response.text
                except ImportError:
                    from urllib.request import Request, urlopen

                    request = Request(url, headers={"User-Agent": self.user_agent})
                    with urlopen(request, timeout=self.timeout) as response:
                        return response.read().decode("utf-8", errors="replace")
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
        raise RuntimeError(f"Could not fetch {url}: {last_error}")

    def extract_from_page(self, page_url: str, page_text: str, links: Iterable[Tuple[str, str]]) -> List[Dict]:
        candidates: List[Dict] = []

        for label, link in links:
            searchable = f"{label} {link}"
            if not label or not self.is_real_opportunity(searchable):
                continue
            candidates.append(self.make_opportunity(label, link, page_url, page_text))

        if not candidates and self.is_real_opportunity(page_text):
            title = self._best_title_from_text(page_text)
            candidates.append(self.make_opportunity(title, page_url, page_url, page_text))

        return candidates

    def is_real_opportunity(self, text: str) -> bool:
        normalized = " ".join((text or "").lower().split())
        if not normalized:
            return False
        if any(term in normalized for term in self.EXCLUDED_TERMS):
            return False
        has_required_term = any(term in normalized for term in self.REQUIRED_OPPORTUNITY_TERMS)
        if not has_required_term:
            return False
        is_news = "news" in normalized or "/news" in normalized
        has_deadline = "deadline" in normalized or "closing date" in normalized
        if is_news and not has_deadline:
            return False
        return True

    def make_opportunity(self, title: str, link: str, source_url: str, context_text: str) -> Dict:
        title = " ".join((title or "Opportunity signal").split())[:240]
        summary = " ".join((context_text or "").split())[:800]
        return {
            "title": title,
            "procuring_entity": self.source_name,
            "tender_reference": self._extract_reference(f"{title} {summary}"),
            "procurement_type": "",
            "opportunity_category": "",
            "sector": "",
            "deadline": self._extract_deadline(f"{title} {summary}"),
            "publication_date": datetime.now(timezone.utc).date().isoformat(),
            "source_platform": self.source_platform,
            "source_group": self.source_group,
            "source_website": self._domain(source_url),
            "original_link": link,
            "document_links": [link] if self._looks_like_document(link) else [],
            "ppp_flag": self.ppp_flag,
            "newspaper_flag": self.newspaper_flag,
            "social_signal_flag": self.social_signal_flag,
            "donor_funded_flag": self.donor_funded_flag,
            "manual_review_flag": self.social_signal_flag or not self._extract_deadline(f"{title} {summary}"),
            "raw_text_summary": summary,
        }

    def _best_title_from_text(self, text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
        for sentence in sentences:
            if 20 <= len(sentence) <= 220:
                return sentence
        return text[:220] or "Opportunity signal"

    def _extract_reference(self, text: str) -> str:
        patterns = [
            r"(?:Tender|Bid|Reference|Ref\.?|Procurement)\s*(?:No\.?|Number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-_.]{3,})",
            r"\b([A-Z]{2,}\/[A-Z0-9\/\-_.]{4,})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1)[:80]
        return ""

    def _extract_deadline(self, text: str) -> str:
        match = re.search(
            r"(?:deadline|closing date|closes|submission date)[^\d]{0,30}(\d{1,2}[\/\-. ](?:\d{1,2}|[A-Za-z]{3,9})[\/\-. ]\d{2,4})",
            text,
            re.I,
        )
        return match.group(1) if match else ""

    def _domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or url

    def _looks_like_document(self, url: str) -> bool:
        return any(url.lower().split("?")[0].endswith(ext) for ext in (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"))
