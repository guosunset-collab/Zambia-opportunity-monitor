from html.parser import HTMLParser
from typing import List, Tuple
from urllib.parse import urljoin


class LinkTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: List[Tuple[str, str]] = []
        self.text_parts: List[str] = []
        self._current_href = None
        self._current_text: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get("href")
            self._current_text = []

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._current_href:
            text = " ".join(part.strip() for part in self._current_text if part.strip())
            self.links.append((text, self._current_href))
            self._current_href = None
            self._current_text = []

    def handle_data(self, data):
        clean = " ".join(data.split())
        if clean:
            self.text_parts.append(clean)
            if self._current_href:
                self._current_text.append(clean)


def extract_text_and_links(html: str, base_url: str = "") -> Tuple[str, List[Tuple[str, str]]]:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        links = []
        for anchor in soup.find_all("a", href=True):
            label = " ".join(anchor.get_text(" ").split())
            links.append((label, urljoin(base_url, anchor["href"])))
        return text, links
    except Exception:
        parser = LinkTextParser()
        parser.feed(html)
        text = " ".join(parser.text_parts)
        links = [(label, urljoin(base_url, href)) for label, href in parser.links]
        return text, links
