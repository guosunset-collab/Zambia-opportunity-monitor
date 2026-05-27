import unittest

from report import generate_markdown
from scrapers.base import SourceScraper


class FilteringScraper(SourceScraper):
    source_name = "Test Source"
    source_platform = "Government Procurement"


class CloudRefactorTests(unittest.TestCase):
    def test_filters_only_real_opportunity_links(self):
        scraper = FilteringScraper({}, {"max_items_per_source": 10}, logger=None)
        links = [
            ("Homepage", "https://example.test/"),
            ("Contact", "https://example.test/contact"),
            ("Invitation for bids: road works contract closing date 30 June 2026", "https://example.test/tender-road"),
            ("Airport services news", "https://example.test/airport-services"),
            ("Training on public procurement act", "https://example.test/training"),
        ]

        items = scraper.extract_from_page("https://example.test", "Welcome to the homepage", links)

        self.assertEqual(1, len(items))
        self.assertIn("Invitation for bids", items[0]["title"])

    def test_report_groups_opportunities_by_requested_source_sections(self):
        items = [
            {
                "title": "Road works contract",
                "procuring_entity": "Road Development Agency",
                "source_platform": "Government Procurement",
                "source_group": "Road & Transport",
                "priority": "HIGH",
                "ppp_flag": False,
                "newspaper_flag": False,
                "donor_funded_flag": False,
                "raw_text_summary": "Tender with closing date.",
            },
            {
                "title": "PPP concession EOI",
                "procuring_entity": "Ministry of Finance",
                "source_platform": "PPP / Investment",
                "source_group": "PPP / Investment",
                "priority": "HIGH",
                "ppp_flag": True,
                "newspaper_flag": False,
                "donor_funded_flag": False,
                "raw_text_summary": "Expression of interest with deadline.",
            },
        ]

        markdown = generate_markdown(items, "2026-05-27", duplicate_count=0)

        self.assertIn("## Executive Brief", markdown)
        self.assertIn("- Total new opportunities: 2", markdown)
        self.assertIn("- PPP signals: 1", markdown)
        self.assertIn("## Road & Transport (RDA / NRFA / RTSA)", markdown)
        self.assertIn("### Road works contract", markdown)
        self.assertIn("## PPP / Investment", markdown)
        self.assertIn("### PPP concession EOI", markdown)


if __name__ == "__main__":
    unittest.main()
