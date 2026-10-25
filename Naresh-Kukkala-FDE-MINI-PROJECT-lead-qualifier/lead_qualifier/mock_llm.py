"""Offline stand-in for an LLM (`--provider mock`).

It honours the exact same JSON contract as the real prompt, so the whole pipeline —
batching, parsing, validation, fallback — is exercised without an API key. It can
also inject failures to demonstrate retry/fallback behaviour:
    MOCK_FAIL_RATE=0.3       fraction of calls that raise a retryable 5xx-style error
    MOCK_MALFORMED_RATE=0.2  fraction of calls that return broken JSON
"""
from __future__ import annotations

import json
import os
import random
import re

from .messages import template_message

KEYWORD_TIERS = [
    (("saas", "software", "tech", "cloud", "ai", "data", "cyber", "devops", "it "), "core", 0.85),
    (("bank", "financ", "insur", "health", "logistic", "retail", "manufactur", "consult", "service", "legal",
      "media", "marketing", "energy", "pharma", "biotech", "real estate", "education", "telecom"), "adjacent", 0.75),
    (("hospitality", "restaurant", "event", "agri", "farm", "nonprofit", "government", "sport", "travel",
      "art", "cultural", "leisure"), "low", 0.75),
]


class MockLLM:
    def __init__(self, company_cfg: dict):
        self.company_cfg = company_cfg
        self.fail_rate = float(os.getenv("MOCK_FAIL_RATE", "0"))
        self.malformed_rate = float(os.getenv("MOCK_MALFORMED_RATE", "0"))
        self.rng = random.Random(int(os.getenv("MOCK_SEED", "7")))

    def complete(self, system: str, user: str) -> str:
        from .llm import LLMError
        if self.rng.random() < self.fail_rate:
            raise LLMError("mock: simulated 503 Service Unavailable")
        payload = json.loads(user[user.index("{"):])
        company_cfg = self.company_cfg
        out = []
        for lead in payload["leads"]:
            tier, conf = None, 0.0
            if lead.get("classify_industry"):
                s = (lead.get("industry") or "").lower() + " "
                for keys, t, c in KEYWORD_TIERS:
                    if any(re.search(r"\b" + re.escape(k.strip()), s) for k in keys):
                        tier, conf = t, c
                        break
            flags = []
            comp = (lead.get("company") or "").lower()
            if re.search(r"\b(test|example|acme|dummy|sample)\b", comp):
                flags.append({"flag": "company name looks like test/placeholder data", "severity": "high"})
            if re.search(r"\b(failed|defunct|shutdown|closed|bankrupt)\b", comp):
                flags.append({"flag": "company name suggests it may have shut down", "severity": "high"})
            if "government" in (lead.get("industry") or "").lower() or "government" in comp:
                flags.append({"flag": "public-sector buyer: expect formal procurement/RFP", "severity": "low"})
            if (lead.get("company_size") or 0) > 20000:
                flags.append({"flag": "very large enterprise: multi-stakeholder, long cycle", "severity": "low"})
            msg = None
            if lead.get("write_message"):
                m = template_message(lead, company_cfg, lead.get("variant"))
                msg = {"subject": m["subject"], "body": m["body"]}
            angle = (f"{lead.get('source') or 'Unknown-source'} lead from {lead.get('company') or 'unnamed company'}"
                     f" ({lead.get('industry') or 'industry unknown'}); lead with response-time pain.")
            out.append({"id": lead["id"], "industry_tier": tier, "industry_confidence": conf,
                        "risk_flags": flags, "sales_angle": angle, "message": msg})
        text = json.dumps({"leads": out})
        if self.rng.random() < self.malformed_rate:
            return "Sure! Here is the JSON:\n" + text[: len(text) // 2]  # truncated -> parse error
        return text
