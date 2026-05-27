import re
from typing import Dict, Tuple


HIGH_KEYWORDS = {
    "road", "roads", "highway", "bridge", "bridges", "transport corridor",
    "civil infrastructure", "civil works", "epc", "design-build", "design build",
    "supervision", "consultancy", "ppp", "concession", "bot", "boot", "dbfo",
    "asphalt", "pavement", "earthworks", "culvert", "culverts",
}

MEDIUM_KEYWORDS = {
    "water", "sewerage", "utility", "utilities", "building", "buildings",
    "airport", "aviation", "runway", "taxiway", "apron", "drainage",
    "street lighting", "maintenance", "materials",
}

LOW_KEYWORDS = {
    "stationery", "furniture", "office supplies", "toner", "laptop",
    "desktop computer", "printer cartridge",
}

IMPORTANT_ENTITIES = {
    "road development agency", "zambia public procurement authority",
    "national road fund agency", "zambia airports", "zesco",
    "ministry of finance", "world bank", "african development bank",
}


def _text_for_scoring(item: Dict) -> str:
    parts = [
        item.get("title", ""),
        item.get("procuring_entity", ""),
        item.get("procurement_type", ""),
        item.get("opportunity_category", ""),
        item.get("sector", ""),
        item.get("raw_text_summary", ""),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def detect_flags(item: Dict) -> Dict:
    text = _text_for_scoring(item)
    source_platform = str(item.get("source_platform", "")).lower()
    source_website = str(item.get("source_website", "")).lower()

    item["ppp_flag"] = bool(item.get("ppp_flag")) or any(
        token in text for token in ("ppp", "concession", "bot", "boot", "dbfo", "public private partnership")
    )
    item["newspaper_flag"] = bool(item.get("newspaper_flag")) or "newspaper" in source_platform
    item["social_signal_flag"] = bool(item.get("social_signal_flag")) or any(
        token in source_platform + " " + source_website for token in ("facebook", "twitter", "x.com", "linkedin", "telegram")
    )
    item["donor_funded_flag"] = bool(item.get("donor_funded_flag")) or any(
        token in source_platform + " " + source_website + " " + text
        for token in ("world bank", "afdb", "african development bank", "jica", "un procurement", "european union", "donor")
    )
    return item


def score_opportunity(item: Dict) -> Dict:
    item = detect_flags(dict(item))
    text = _text_for_scoring(item)
    score = 0
    reasons = []

    high_hits = sorted(keyword for keyword in HIGH_KEYWORDS if keyword in text)
    medium_hits = sorted(keyword for keyword in MEDIUM_KEYWORDS if keyword in text)
    low_hits = sorted(keyword for keyword in LOW_KEYWORDS if keyword in text)

    if high_hits:
        score += 70
        reasons.append("high-priority infrastructure terms: " + ", ".join(high_hits[:5]))
    if medium_hits:
        score += 35
        reasons.append("medium-priority infrastructure terms: " + ", ".join(medium_hits[:5]))
    if any(entity in text for entity in IMPORTANT_ENTITIES):
        score += 15
        reasons.append("important procuring entity or donor")
    if item.get("ppp_flag"):
        score += 20
        reasons.append("PPP/concession/investment signal")
    if item.get("donor_funded_flag"):
        score += 10
        reasons.append("donor-funded signal")
    if item.get("social_signal_flag"):
        score += 5
        reasons.append("early social-media signal")
    if low_hits and not high_hits and not medium_hits:
        score -= 25
        reasons.append("likely non-infrastructure procurement")

    score = max(0, min(score, 100))
    if score >= 70:
        relevance = "HIGH"
    elif score >= 35:
        relevance = "MEDIUM"
    else:
        relevance = "LOW"

    item["relevance_score"] = score
    item["priority"] = relevance
    item["recommendation_reason"] = "; ".join(reasons) if reasons else "No strong infrastructure signal detected yet."
    item["manual_review_flag"] = bool(item.get("manual_review_flag")) or bool(item.get("social_signal_flag")) or not bool(item.get("deadline"))

    if not item.get("sector"):
        item["sector"] = infer_sector(text)
    if not item.get("opportunity_category"):
        item["opportunity_category"] = infer_category(text)
    if not item.get("procurement_type"):
        item["procurement_type"] = infer_procurement_type(text)

    return item


def infer_sector(text: str) -> str:
    checks: Tuple[Tuple[str, str], ...] = (
        ("Roads / Transport", "road|highway|bridge|pavement|asphalt|transport corridor|culvert"),
        ("Airports / Aviation", "airport|aviation|runway|taxiway|apron"),
        ("Water / Utilities", "water|sewerage|utility|utilities|zesco"),
        ("Buildings / Public Facilities", "building|public facility|school|hospital"),
        ("Civil Infrastructure", "civil works|earthworks|drainage|infrastructure"),
    )
    for label, pattern in checks:
        if re.search(pattern, text):
            return label
    return "Unclassified"


def infer_category(text: str) -> str:
    if any(token in text for token in ("ppp", "concession", "bot", "boot", "dbfo")):
        return "PPP / Investment"
    if "expression of interest" in text or " eoi" in text:
        return "Expression of Interest"
    if "request for proposal" in text or " rfp" in text:
        return "Request for Proposals"
    if "request for quotation" in text or " rfq" in text:
        return "Request for Quotations"
    if "prequalification" in text:
        return "Prequalification"
    if any(token in text for token in ("corrigendum", "addendum", "clarification", "extension")):
        return "Clarification / Addendum"
    if any(token in text for token in ("tender", "bid", "procurement")):
        return "Tender / Bid Invitation"
    return "Opportunity Signal"


def infer_procurement_type(text: str) -> str:
    if "consult" in text or "supervision" in text or "design" in text:
        return "Consultancy / Professional Services"
    if "works" in text or "construction" in text or "rehabilitation" in text:
        return "Works"
    if "supply" in text or "materials" in text:
        return "Goods / Materials"
    if "ppp" in text or "concession" in text:
        return "PPP / Concession"
    return "Unspecified"
