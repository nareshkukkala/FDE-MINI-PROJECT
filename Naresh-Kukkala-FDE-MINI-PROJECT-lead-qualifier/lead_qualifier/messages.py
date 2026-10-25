"""Deterministic outreach templates.

Used (a) by the offline mock provider and (b) as the FALLBACK whenever an LLM call fails
or returns a message that fails validation — so a qualified lead always gets a usable,
personalised draft, clearly labelled as template-generated.
"""
from __future__ import annotations

import re
from typing import Optional

VARIANT_BY_SOURCE = {
    "Inbound demo request": "inbound_followup",
    "Sales call": "inbound_followup",
    "Referral": "warm_intro",
    "Webinar attendee": "warm_intro",
    "Content download": "value_first",
    "LinkedIn outreach": "value_first",
}

# Industry-specific pain points: keyword -> phrase. First match wins.
PAIN_POINTS = [  # ordered specific -> generic ("fintech" must match before "tech")
    (("fintech", "insurtech", "finance", "bank", "insur", "crypto", "blockchain"), "high-intent applicants waiting days for a compliant first response"),
    (("healthtech", "health", "pharma", "biotech", "medical"), "provider and partner enquiries stuck in shared inboxes"),
    (("edtech", "education", "learning"), "institutional enquiries slipping between admissions, sales and partnerships"),
    (("logistic", "supply", "trade", "automotive", "manufactur", "construction"), "RFQs and distributor enquiries routed by hand across regions"),
    (("retail", "consumer", "fashion", "ecommerce"), "wholesale and partnership enquiries mixed in with customer-service tickets"),
    (("marketing", "media", "agency", "entertainment"), "new-business enquiries that depend on whoever checks the inbox first"),
    (("consult", "legal", "services", "real estate", "hr"), "referral and inbound enquiries tracked in spreadsheets"),
    (("energy", "climate", "environment"), "commercial project enquiries with long, multi-stakeholder follow-up"),
    (("saas", "software", "tech", "ai", "analytics", "cyber", "data", "telecom"), "trial sign-ups and demo requests going cold before an AE ever replies"),
]
DEFAULT_PAIN = "promising leads waiting too long for a first response"


def pain_point(industry: Optional[str]) -> str:
    s = (industry or "").lower()
    for keys, phrase in PAIN_POINTS:
        if any(k in s for k in keys):
            return phrase
    return DEFAULT_PAIN


def variant_for(source: Optional[str]) -> str:
    return VARIANT_BY_SOURCE.get(source or "", "value_first")


def _first_name(name: Optional[str]) -> Optional[str]:
    if not name or "_" in name:  # "Test_Solo" style labels are not real names
        return None
    return name.split()[0]


def _recency_phrase(days: Optional[int]) -> str:
    if days is None:
        return "recently"
    if days <= 1:
        return "today"
    if days <= 7:
        return "earlier this week"
    if days <= 31:
        return "a few weeks ago"
    return "a little while back"


def _possessive(company: str) -> str:
    return f"{company}'" if company.endswith("s") else f"{company}'s"


def _size_phrase(size: Optional[int]) -> str:
    if size is None:
        return "a growing team"
    if size < 50:
        return f"a {size}-person team"
    if size <= 1000:
        return f"a team of about {size}"
    return f"an organisation of {size:,} people"


def template_message(lead: dict, company_cfg: dict, variant: Optional[str] = None) -> dict:
    """lead dict keys: name, company, company_size, industry, source, days_since_last_touch."""
    variant = variant or variant_for(lead.get("source"))
    first = _first_name(lead.get("name"))
    hi = f"Hi {first}," if first else "Hi there,"
    company = lead.get("company") or "your team"
    industry = lead.get("industry") or "your market"
    size = _size_phrase(lead.get("company_size"))
    when = _recency_phrase(lead.get("days_since_last_touch"))
    pain = pain_point(lead.get("industry"))
    product, proof = company_cfg["product_name"], company_cfg["proof_point"]
    sign = f"\n\nBest,\n{company_cfg['sender_name']}\n{company_cfg['sender_title']}"

    if variant == "inbound_followup":
        subject = f"Your {product} demo for {company}"
        opener = (f"Thanks for the conversation {when}." if lead.get("source") == "Sales call"
                  else f"Thanks for requesting a demo {when}.")
        body = (f"{hi}\n\n{opener} For {size} in {industry}, the usual bottleneck is {pain}, "
                f"so I'd tailor the demo around how {company} could route and follow up on those automatically. "
                f"With {product}, {proof}.\n\nWould Tuesday at 11:00 or Thursday at 15:00 work for a 30-minute walkthrough? "
                f"Happy to fit around your calendar.")
    elif variant == "warm_intro":
        how = "the webinar" if lead.get("source") == "Webinar attendee" else "a mutual connection's introduction"
        subject = f"Following up from {how.replace('a ', '')}"
        body = (f"{hi}\n\nGreat to connect via {how} {when}. Many {industry} teams like {company} ({size}) tell us "
                f"their biggest leak is {pain}.\n\nOut of curiosity, how does {company} decide today which inbound "
                f"leads get a same-day reply? If it's useful, I can share how similar teams use {product} — {proof}.")
    else:  # value_first
        subject = f"Faster lead follow-up at {company}"
        body = (f"{hi}\n\nI noticed {_possessive(company)} interest in our work {when}. For {size} in {industry}, "
                f"one pattern we see often is {pain} — and response time is usually the cheapest win available.\n\n"
                f"{product} is {company_cfg['one_liner']}; {proof}. Would a two-page teardown of how that could look "
                f"for {company} be useful? No call needed unless it is.")
    return {"subject": subject, "body": body + sign, "variant": variant}


def validate_message(msg, lead: dict) -> Optional[str]:
    """Return None if the LLM message is acceptable, else the reason it was rejected."""
    if not isinstance(msg, dict) or not msg.get("body") or not msg.get("subject"):
        return "missing subject/body"
    body = msg["body"]
    if re.search(r"\[[A-Za-z _]+\]|\{\{|<[A-Z_]+>", body):
        return "contains template placeholders"
    company = (lead.get("company") or "").lower()
    if company and company not in body.lower() and company not in msg["subject"].lower():
        return "does not mention the company (not personalised)"
    words = len(body.split())
    if words < 30 or words > 220:
        return f"length {words} words outside 30-220"
    return None
