from scrapers.base import SourceScraper


class ZambiaDailyMailScraper(SourceScraper):
    source_name = "Zambia Daily Mail"
    source_platform = "Newspaper"
    source_group = "Newspapers"
    newspaper_flag = True

    # TODO: Add e-paper PDF issue discovery and OCR parsing for scanned public notices.
