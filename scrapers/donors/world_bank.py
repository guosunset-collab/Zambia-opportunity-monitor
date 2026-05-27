from scrapers.base import SourceScraper


class WorldBankScraper(SourceScraper):
    source_name = "World Bank Zambia"
    source_platform = "Donor Procurement"
    source_group = "Donor-funded"
    donor_funded_flag = True
