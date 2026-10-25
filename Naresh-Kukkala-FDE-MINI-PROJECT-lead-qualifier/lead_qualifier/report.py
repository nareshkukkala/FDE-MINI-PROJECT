"""Build the outputs: output_report.json (full), output_report.csv (flat, for the CRM),
and sales_summary.md (what a sales manager reads on Monday morning)."""
from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import datetime

from .rubric import QUALIFIED, REJECTED, REVIEW


def _lead_row(rec: dict) -> dict:
    l, a = rec["lead"], rec["a"]
    return {
        "lead_id": l.lead_id, "rank": rec["rank"], "name": l.name, "company": l.company,
        "company_size": l.company_size, "industry": l.industry, "source": l.source,
        "last_interaction_date": l.last_interaction_date.isoformat() if l.last_interaction_date else None,
        "days_since_last_touch": a.days_since_interaction,
        "score": a.score, "score_range": list(a.score_range), "decision": a.decision,
        "priority": rec["priority"], "sla": rec["sla"],
        "factor_breakdown": {k: {"points": f.points, "max": f.max_points, "detail": f.detail} for k, f in a.factors.items()},
        "industry_tier": a.industry_tier, "industry_tier_source": a.industry_tier_source,
        "reasoning": a.reasons,
        "rejection_reasons": a.rejection_reasons, "review_reasons": a.review_reasons,
        "ai_risk_flags": (rec["llm"] or {}).get("risk_flags", []),
        "sales_angle": (rec["llm"] or {}).get("sales_angle"),
        "outreach_message": rec["message"], "message_source": rec["message_source"],
        "llm_status": rec["llm_status"], "data_issues": l.data_issues, "source_row": l.row_number,
    }


def _samples(records: list[dict], n: int = 5) -> list[dict]:
    """Pick up to n messages covering every variant, preferring top-ranked qualified leads."""
    pool = [r for r in records if r["message"] and r["a"].decision == QUALIFIED] or [r for r in records if r["message"]]
    out, seen = [], set()
    for r in pool:  # one per variant first
        v = r["message"].get("variant")
        if v not in seen:
            seen.add(v)
            out.append(r)
    variants = list(dict.fromkeys(r["message"].get("variant") for r in pool))
    queues = {v: [r for r in pool if r["message"].get("variant") == v and r not in out] for v in variants}
    while len(out) < n and any(queues.values()):  # round-robin so samples show variety
        for v in variants:
            if queues[v] and len(out) < n:
                out.append(queues[v].pop(0))
    return [{"lead_id": r["lead"].lead_id, "company": r["lead"].company, "contact": r["lead"].name,
             "score": r["a"].score, "variant": r["message"].get("variant"), "message_source": r["message_source"],
             "subject": r["message"]["subject"], "body": r["message"]["body"]} for r in out[:n]]


def build_report(result: dict) -> dict:
    recs = result["records"]
    total = len(recs)
    by = Counter(r["a"].decision for r in recs)
    pct = lambda x: round(100.0 * x / total, 1) if total else 0.0
    rej = Counter(reason for r in recs if r["a"].decision == REJECTED for reason in r["a"].rejection_reasons)
    rev = Counter(reason.split(":")[0] if reason.startswith("AI red flag") else reason
                  for r in recs if r["a"].decision == REVIEW for reason in r["a"].review_reasons)
    issues = Counter(i.split("'")[0].strip() for r in recs for i in r["lead"].data_issues)
    qual = [r for r in recs if r["a"].decision == QUALIFIED]
    rubric = result["rubric"]
    stats = result["llm_stats"]
    alerts = list(result["events"])
    fb = sum(1 for r in recs if r["llm_status"] == "fallback")
    if fb:
        alerts.insert(0, f"{fb} lead(s) processed without AI enrichment (rubric-only + template messages). "
                         "Re-run later or review their messages before sending.")
    return {
        "run": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "input_file": os.path.basename(result["input_file"]),
            "analysis_date": result["as_of"].isoformat(),
            "llm_provider": result["provider"], "llm_model": result["model"],
            "batches": result["batches"], "api_calls": stats["api_calls"], "retries": stats["retries"],
            "rate_limited": stats["rate_limited"], "failed_calls": stats["failures"],
            "leads_with_ai_enrichment": sum(1 for r in recs if r["llm_status"] == "ok"),
            "leads_rubric_only_fallback": fb, "duration_seconds": result["duration_s"],
        },
        "rubric": {
            "summary": (f"Score = size fit (0-{rubric.max_pts['size']:g}) + industry fit (0-{rubric.max_pts['industry']:g}) + "
                        f"source intent (0-{rubric.max_pts['source']:g}) + recency (0-{rubric.max_pts['recency']:g}), "
                        f"max 10. >= {rubric.q_min:g} qualified, < {rubric.r_below:g} rejected, in between = human review. "
                        f"Knockouts: < {rubric.min_size} employees or no contact in > {rubric.max_days} days. "
                        "Missing fields are scored as a range; if the range straddles a threshold the lead goes to review. "
                        "AI red flags can move a qualified lead to review but never qualify or reject on their own."),
            "thresholds": rubric.cfg["thresholds"], "knockouts": rubric.cfg["knockouts"],
        },
        "stats": {
            "total_processed": total,
            "qualified": by[QUALIFIED], "qualified_pct": pct(by[QUALIFIED]),
            "review": by[REVIEW], "review_pct": pct(by[REVIEW]),
            "rejected": by[REJECTED], "rejected_pct": pct(by[REJECTED]),
            "p1_count": sum(1 for r in qual if r["priority"] == "P1"),
            "p2_count": sum(1 for r in qual if r["priority"] == "P2"),
            "avg_score": round(sum(r["a"].score for r in recs) / total, 2) if total else 0,
            "common_rejection_reasons": rej.most_common(),
            "common_review_reasons": rev.most_common(),
            "data_quality_issues": issues.most_common(),
            "qualified_by_source": Counter(r["lead"].source or "unknown" for r in qual).most_common(),
            "qualified_by_industry_tier": Counter(r["a"].industry_tier or "unknown" for r in qual).most_common(),
            "est_manual_minutes_saved": total * 10,  # brief: 8-12 min per manual decision
        },
        "alerts": alerts,
        "priority_queue": [{"rank": r["rank"], "lead_id": r["lead"].lead_id, "name": r["lead"].name,
                            "company": r["lead"].company, "score": r["a"].score, "priority": r["priority"],
                            "sla": r["sla"], "source": r["lead"].source,
                            "sales_angle": (r["llm"] or {}).get("sales_angle")} for r in qual],
        "flagged_for_review": [{"rank": r["rank"], "lead_id": r["lead"].lead_id, "name": r["lead"].name,
                                "company": r["lead"].company, "score": r["a"].score,
                                "score_range": list(r["a"].score_range), "why": r["a"].review_reasons,
                                "data_issues": r["lead"].data_issues}
                               for r in recs if r["a"].decision == REVIEW],
        "disqualified": [{"lead_id": r["lead"].lead_id, "name": r["lead"].name, "company": r["lead"].company,
                          "score": r["a"].score, "why": r["a"].rejection_reasons}
                         for r in recs if r["a"].decision == REJECTED],
        "sample_outreach_messages": _samples(recs),
        "leads": [_lead_row(r) for r in recs],
    }


def write_outputs(report: dict, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    paths = {k: os.path.join(out_dir, f) for k, f in
             (("json", "output_report.json"), ("csv", "output_report.csv"), ("md", "sales_summary.md"))}
    with open(paths["json"], "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str, ensure_ascii=False)

    cols = ["rank", "lead_id", "name", "company", "company_size", "industry", "source", "last_interaction_date",
            "days_since_last_touch", "score", "score_min", "score_max", "decision", "priority", "sla",
            "reasoning", "ai_risk_flags", "data_issues", "message_subject", "message_body", "message_source", "llm_status"]
    with open(paths["csv"], "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for l in report["leads"]:
            m = l["outreach_message"] or {}
            w.writerow({**{c: l.get(c) for c in cols if c in l},
                        "score_min": l["score_range"][0], "score_max": l["score_range"][1],
                        "reasoning": " | ".join(l["reasoning"]),
                        "ai_risk_flags": " | ".join(f"{f['severity']}: {f['flag']}" for f in l["ai_risk_flags"]),
                        "data_issues": " | ".join(l["data_issues"]),
                        "message_subject": m.get("subject"), "message_body": m.get("body")})

    s, run = report["stats"], report["run"]
    md = [f"# Lead qualification summary — {run['input_file']}",
          f"Analysis date {run['analysis_date']} · {s['total_processed']} leads · model `{run['llm_provider']}/{run['llm_model']}` "
          f"· {run['api_calls']} API calls in {run['batches']} batches · {run['duration_seconds']}s",
          "", f"**{s['qualified']} qualified ({s['qualified_pct']}%)** — {s['p1_count']} P1, {s['p2_count']} P2 · "
          f"**{s['review']} for review** · **{s['rejected']} rejected**", ""]
    if report["alerts"]:
        md += ["## Alerts"] + [f"- {a}" for a in report["alerts"]] + [""]
    md += ["## Priority queue", "| # | Lead | Company | Score | Priority | Source |", "|---|---|---|---|---|---|"]
    md += [f"| {q['rank']} | {q['name'] or '—'} | {q['company'] or '—'} | {q['score']} | {q['priority']} | {q['source']} |"
           for q in report["priority_queue"]]
    md += ["", "## Needs a human decision", "| Lead | Company | Score (range) | Why |", "|---|---|---|---|"]
    md += [f"| {q['name'] or '—'} | {q['company'] or '—'} | {q['score']} ({q['score_range'][0]}–{q['score_range'][1]}) | "
           f"{'; '.join(q['why'])} |" for q in report["flagged_for_review"]]
    md += ["", "## Top rejection reasons"] + [f"- {r}: {c}" for r, c in s["common_rejection_reasons"][:6]]
    md += ["", "## Sample outreach"]
    for m in report["sample_outreach_messages"]:
        md += [f"### {m['company']} — {m['variant']} ({m['message_source']})", f"**Subject:** {m['subject']}", "",
               m["body"].replace("\n", "  \n"), ""]
    with open(paths["md"], "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    return paths
