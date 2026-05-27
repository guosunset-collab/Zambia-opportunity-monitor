from scrapers.base import SourceScraper


class FacebookScraper(SourceScraper):
    source_name = "Facebook Official Pages"
    source_platform = "Facebook"
    source_group = "Social Media"
    social_signal_flag = True

    # TODO: Replace HTML fallback with Facebook Graph API when page access tokens are available.
