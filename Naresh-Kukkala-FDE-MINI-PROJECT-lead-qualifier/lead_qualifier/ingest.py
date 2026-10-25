"""CSV ingestion, validation and normalisation.

Design rule: a bad row must never crash the run. Every problem is recorded on the
lead as a `data_issue` and the field is set to None ("missing"), so the rubric can
reason explicitly about what it does not know.
"""
from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

log = logging.getLogger(__name__)

EXPECTED_COLUMNS = ["name", "company", "company_size", "industry", "source", "last_interaction_date"]

# Values that mean "we don't know" in real-world CRM exports.
MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-", "unknown", "?", "tbd"}
UNKNOWN_PREFIX = re.compile(r"^(unknown|unmapped|other)\b", re.I)

# Canonical source names + common aliases seen in CRM exports.
SOURCE_ALIASES = {
    "inbound demo request": "Inbound demo request", "demo request": "Inbound demo request",
    "inbound": "Inbound demo request", "website demo": "Inbound demo request",
    "referral": "Referral", "partner referral": "Referral", "customer referral": "Referral",
    "sales call": "Sales call", "discovery call": "Sales call",
    "webinar attendee": "Webinar attendee", "webinar": "Webinar attendee",
    "content download": "Content download", "ebook download": "Content download", "whitepaper": "Content download",
    "linkedin outreach": "LinkedIn outreach", "linkedin": "LinkedIn outreach", "cold outreach": "LinkedIn outreach",
}

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


@dataclass
class Lead:
    lead_id: str
    row_number: int
    raw: dict
    name: Optional[str] = None
    company: Optional[str] = None
    company_size: Optional[int] = None
    industry: Optional[str] = None
    source: Optional[str] = None
    last_interaction_date: Optional[date] = None
    data_issues: list = field(default_factory=list)
    duplicate_of: Optional[str] = None


def _clean(value) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip()
    return None if v.lower() in MISSING_TOKENS else v


def parse_size(value) -> tuple[Optional[int], Optional[str]]:
    """Return (employees, issue). Accepts '50', '1,200', '50+', '11-50', '5k'."""
    v = _clean(value)
    if v is None:
        return None, "company_size missing"
    s = v.lower().replace(",", "").replace("employees", "").strip()
    try:
        if re.fullmatch(r"\d+(\.\d+)?k", s):
            return int(float(s[:-1]) * 1000), None
        m = re.fullmatch(r"(\d+)\s*[-–to]+\s*(\d+)", s)
        if m:  # a range -> midpoint
            lo, hi = int(m.group(1)), int(m.group(2))
            return (lo + hi) // 2, f"company_size given as range '{v}', used midpoint"
        if s.endswith("+"):
            s = s[:-1]
        n = int(float(s))
    except ValueError:
        return None, f"company_size not a number: '{v}'"
    if n <= 0:
        return None, f"company_size invalid: {n}"
    return n, None


def parse_date(value) -> tuple[Optional[date], Optional[str]]:
    v = _clean(value)
    if v is None:
        return None, "last_interaction_date missing"
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date(), None
        except ValueError:
            continue
    return None, f"last_interaction_date unparseable: '{v}'"


def normalise_source(value) -> tuple[Optional[str], Optional[str]]:
    v = _clean(value)
    if v is None or UNKNOWN_PREFIX.match(v):
        return None, "source missing/unknown"
    canon = SOURCE_ALIASES.get(v.lower())
    if canon is None:
        # Keep the raw value; the rubric scores it as an unrecognised source.
        return v, f"source '{v}' not in known list"
    return canon, None


def normalise_industry(value) -> tuple[Optional[str], Optional[str]]:
    v = _clean(value)
    if v is None or UNKNOWN_PREFIX.match(v):
        return None, "industry missing/unknown"
    return v, None


def load_leads(path: str) -> tuple[list[Lead], list[str]]:
    """Read a CSV into Lead objects. Returns (leads, file_level_warnings)."""
    warnings: list[str] = []
    leads: list[Lead] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is empty")
        header = [h.strip().lower() for h in reader.fieldnames]
        missing_cols = [c for c in EXPECTED_COLUMNS if c not in header]
        if missing_cols:
            # Not fatal: the columns are treated as missing on every row.
            warnings.append(f"Missing columns {missing_cols}; those fields are treated as unknown")
        seen: dict[tuple, str] = {}
        for i, row in enumerate(reader, start=2):  # row 1 = header
            row = {(k or "").strip().lower(): v for k, v in row.items()}
            if not any(_clean(v) for v in row.values()):
                warnings.append(f"Row {i}: blank line skipped")
                continue
            lead = Lead(lead_id=f"L{len(leads) + 1:04d}", row_number=i, raw={c: row.get(c) for c in EXPECTED_COLUMNS})
            lead.name = _clean(row.get("name"))
            if lead.name is None:
                lead.data_issues.append("name missing")
            lead.company = _clean(row.get("company"))
            if lead.company is None:
                lead.data_issues.append("company missing")
            for attr, parser in (("company_size", parse_size), ("industry", normalise_industry),
                                 ("source", normalise_source), ("last_interaction_date", parse_date)):
                val, issue = parser(row.get(attr))
                setattr(lead, attr, val)
                if issue:
                    lead.data_issues.append(issue)
            key = ((lead.name or "").lower(), (lead.company or "").lower())
            if key != ("", "") and key in seen:
                lead.duplicate_of = seen[key]
                lead.data_issues.append(f"duplicate of {seen[key]}")
            else:
                seen[key] = lead.lead_id
            leads.append(lead)
    log.info("Loaded %d leads from %s (%d with data issues)", len(leads), path,
             sum(1 for l in leads if l.data_issues))
    return leads, warnings
