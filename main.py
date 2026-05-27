import json
from pathlib import Path
from typing import Dict, List, Type

from logger import get_logger
from report import write_reports
from scoring import score_opportunity
from scrapers.donors.world_bank import WorldBankScraper
from scrapers.government.nrfa import NRFAScraper
from scrapers.government.rda import RDAScraper
from scrapers.government.zambia_airports import ZambiaAirportsScraper
from scrapers.government.zppa import ZPPAScraper
from scrapers.newspapers.zambia_daily_mail import ZambiaDailyMailScraper
from scrapers.ppp.ministry_finance_ppp import MinistryFinancePPPScraper
from scrapers.social.facebook import FacebookScraper
from storage import init_db, upsert_opportunities


SCRAPER_REGISTRY: Dict[str, Type] = {
    "government.zppa": ZPPAScraper,
    "government.rda": RDAScraper,
    "government.nrfa": NRFAScraper,
    "government.zambia_airports": ZambiaAirportsScraper,
    "ppp.ministry_finance_ppp": MinistryFinancePPPScraper,
    "donors.world_bank": WorldBankScraper,
    "newspapers.zambia_daily_mail": ZambiaDailyMailScraper,
    "social.facebook": FacebookScraper,
}


DEFAULT_CONFIG = {
    "run": {
        "timezone": "Africa/Lusaka",
        "output_dir": "reports",
        "database_path": "database/opportunities.sqlite3",
        "log_dir": "logs",
        "max_items_per_source": 25,
        "request_timeout_seconds": 20,
        "retries": 2,
        "user_agent": "Zambia-Infrastructure-Opportunity-Monitor/0.1",
    },
    "email": {
        "enabled": False,
    },
    "sources": {
        "government": {
            "zppa": {"enabled": True, "urls": ["https://eprocure.zppa.org.zm/", "https://www.zppa.org.zm/"]},
            "rda": {"enabled": True, "urls": ["https://www.rda.org.zm/"]},
            "nrfa": {"enabled": True, "urls": ["https://nrfa.org.zm/"]},
            "zambia_airports": {"enabled": True, "urls": ["https://www.zacl.co.zm/"]},
        },
        "ppp": {"ministry_finance_ppp": {"enabled": True, "urls": ["https://www.mofnp.gov.zm/"]}},
        "donors": {"world_bank": {"enabled": True, "urls": ["https://projects.worldbank.org/en/projects-operations/procurement?lang=en&searchTerm=&countrycode_exact=ZM"]}},
        "newspapers": {"zambia_daily_mail": {"enabled": True, "urls": ["https://www.daily-mail.co.zm/"]}},
        "social": {"facebook": {"enabled": True, "urls": ["https://www.facebook.com/RoadDevelopmentAgency/"]}},
    },
}


def load_config(path: str = "config.yaml") -> Dict:
    config_path = Path(path)
    if not config_path.exists():
        config_path = Path("config.example.yaml")
    if not config_path.exists():
        return DEFAULT_CONFIG

    text = config_path.read_text(encoding="utf-8")
    try:
        import yaml

        loaded = yaml.safe_load(text) or {}
    except Exception:
        if config_path.name == "config.example.yaml":
            return DEFAULT_CONFIG
        loaded = json.loads(text)
    return _merge(DEFAULT_CONFIG, loaded)


def _merge(base: Dict, override: Dict) -> Dict:
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def iter_enabled_sources(config: Dict):
    for group_name, group_config in config.get("sources", {}).items():
        for source_name, source_config in (group_config or {}).items():
            if not source_config or not source_config.get("enabled", False):
                continue
            registry_key = f"{group_name}.{source_name}"
            scraper_class = SCRAPER_REGISTRY.get(registry_key)
            if scraper_class:
                yield registry_key, source_config, scraper_class


def run() -> int:
    config = load_config()
    run_config = config.get("run", {})
    logger = get_logger(log_dir=run_config.get("log_dir", "logs"))
    logger.info("Starting Zambia infrastructure opportunity monitor")

    all_candidates: List[Dict] = []
    for registry_key, source_config, scraper_class in iter_enabled_sources(config):
        logger.info(f"Scraping {registry_key}")
        scraper = scraper_class(source_config, run_config, logger)
        try:
            candidates = scraper.scrape()
            logger.info(
                f"Scraper completed: {registry_key}",
                extra={"extra_fields": {"source": registry_key, "candidate_count": len(candidates)}},
            )
            all_candidates.extend(candidates)
        except Exception as exc:
            logger.warning(
                f"Scraper isolated failure: {registry_key}",
                extra={"extra_fields": {"source": registry_key, "error": str(exc)}},
            )

    scored_items = [score_opportunity(item) for item in all_candidates]
    conn = init_db(run_config.get("database_path", "database/opportunities.sqlite3"))
    new_items, duplicate_count = upsert_opportunities(conn, scored_items)
    md_path, html_path = write_reports(new_items, run_config.get("output_dir", "reports"), duplicate_count)

    logger.info(
        "Report generated",
        extra={"extra_fields": {"markdown": str(md_path), "html": str(html_path), "new_items": len(new_items)}},
    )
    logger.info("Email sending disabled for GitHub Actions cloud execution")

    print(f"Report saved: {md_path}")
    print(f"HTML report saved: {html_path}")
    print(f"New opportunities: {len(new_items)}; duplicates skipped: {duplicate_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
