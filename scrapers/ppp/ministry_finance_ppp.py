from scrapers.base import SourceScraper


class MinistryFinancePPPScraper(SourceScraper):
    source_name = "Ministry of Finance and National Planning PPP"
    source_platform = "PPP / Investment"
    source_group = "PPP / Investment"
    ppp_flag = True

    # TODO: Replace or supplement with the dedicated PPP Unit/Council URL once a stable public endpoint is confirmed.
