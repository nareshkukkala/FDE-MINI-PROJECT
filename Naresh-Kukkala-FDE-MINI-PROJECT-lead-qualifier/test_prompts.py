#!/usr/bin/env python3
"""Prompt sanity check: send ONE small batch (default 8 hand-picked leads) to the real LLM and
print the raw JSON plus a validation verdict per lead. Run this before a full batch.

    export GROQ_API_KEY=...   # or ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY
    python3 test_prompts.py --provider groq
"""
import argparse
import json

import yaml

from lead_qualifier.ingest import load_leads
from lead_qualifier.llm import LLMClient
from lead_qualifier.messages import validate_message
from lead_qualifier.pipeline import lead_payload, resolve_as_of
from lead_qualifier.prompts import build_system_prompt, build_user_prompt
from lead_qualifier.rubric import Rubric

# A spread of cases: ideal fit, enterprise, unknown industry, test-looking record, failed startup,
# government, cold outbound, referral.
PICK = ["Test_HighValueMatch", "Test_VeryLargeEnterprise", "Test_UnknownIndustry", "Test_MissingSize",
        "Test_StartupShutdown", "Test_GovernmentBuyer", "Test_WeekOldInteraction", "Test_SMBAverage"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider")
    ap.add_argument("--csv", default="data/leads_testing.csv")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    leads, _ = load_leads(args.csv)
    chosen = [l for l in leads if l.name in PICK] or leads[:8]
    rubric = Rubric(cfg["rubric"], resolve_as_of(cfg["rubric"]["as_of_date"], leads))
    payload = [lead_payload(l, rubric.assess(l), rubric, write_message=True) for l in chosen]
    client = LLMClient(cfg["llm"], args.provider, company_cfg=cfg["company"])
    print(f"Provider: {client.provider} / {client.model} — sending {len(payload)} leads in ONE call\n")
    data = client.complete_json(build_system_prompt(cfg["company"]), build_user_prompt(payload))
    by_id = {str(x.get("id")): x for x in data.get("leads", [])}
    for p in payload:
        r = by_id.get(p["id"])
        print("=" * 80)
        print(f"{p['id']} {p['name']} @ {p['company']} ({p['industry']}, {p['company_size']}, {p['source']})")
        if not r:
            print("  !! missing from response")
            continue
        print(f"  industry_tier={r.get('industry_tier')} conf={r.get('industry_confidence')}")
        print(f"  flags={json.dumps(r.get('risk_flags'))}")
        print(f"  angle={r.get('sales_angle')}")
        problem = validate_message(r.get("message"), p)
        print(f"  message check: {'PASS' if problem is None else 'FAIL - ' + problem}")
        if r.get("message"):
            print(f"  subject: {r['message'].get('subject')}\n  " + r["message"].get("body", "").replace("\n", "\n  "))
    print(f"\nStats: {client.stats}")


if __name__ == "__main__":
    main()
