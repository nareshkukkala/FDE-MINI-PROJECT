"""Orchestration: intake -> rubric pre-score -> batched LLM enrichment -> final decision -> rank.

Failure strategy for each batch:
    1. LLMClient retries transient errors (429/5xx/timeout/malformed JSON) with exponential backoff.
    2. If the batch still fails, split it in half once and retry each half (isolates a poison lead
       or an over-long response without dropping to one-call-per-lead).
    3. Anything still failing gets deterministic fallback: rubric-only scoring + template message,
       labelled `llm_status = "fallback"` in the report.
    4. After N consecutive batch failures the circuit breaker opens and remaining leads go straight
       to fallback, so a dead API never stalls the run.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Optional

from .ingest import Lead, load_leads
from .llm import CircuitOpen, LLMClient, LLMError
from .messages import template_message, validate_message, variant_for
from .prompts import build_system_prompt, build_user_prompt
from .rubric import QUALIFIED, REJECTED, REVIEW, Rubric

log = logging.getLogger(__name__)
VALID_TIERS = {"core", "adjacent", "low"}


def resolve_as_of(setting, leads: list[Lead]) -> date:
    if setting and str(setting).lower() not in ("auto", "today"):
        return date.fromisoformat(str(setting))
    if str(setting).lower() == "today":
        return date.today()
    dates = [l.last_interaction_date for l in leads if l.last_interaction_date]
    return max(dates) if dates else date.today()


def lead_payload(lead: Lead, a, rubric: Rubric, write_message: bool) -> dict:
    return {
        "id": lead.lead_id, "name": lead.name, "company": lead.company, "company_size": lead.company_size,
        "industry": lead.industry, "source": lead.source, "days_since_last_touch": a.days_since_interaction,
        "classify_industry": bool(lead.industry) and rubric.known_industry_tier(lead.industry) is None,
        "write_message": write_message, "variant": variant_for(lead.source),
    }


def _sanitise(item: dict) -> dict:
    """Coerce one LLM result into a safe shape; bad fields become None/[] rather than crashing."""
    tier = item.get("industry_tier")
    tier = tier.lower() if isinstance(tier, str) and tier.lower() in VALID_TIERS else None
    try:
        conf = max(0.0, min(1.0, float(item.get("industry_confidence") or 0)))
    except (TypeError, ValueError):
        conf = 0.0
    flags = []
    for f in item.get("risk_flags") or []:
        if isinstance(f, dict) and f.get("flag"):
            flags.append({"flag": str(f["flag"])[:200], "severity": "high" if f.get("severity") == "high" else "low"})
    return {"industry_tier": tier, "industry_confidence": conf, "risk_flags": flags,
            "sales_angle": str(item.get("sales_angle") or "")[:300] or None, "message": item.get("message")}


class Pipeline:
    def __init__(self, config: dict, provider: Optional[str] = None, model: Optional[str] = None,
                 batch_size: Optional[int] = None):
        self.config = config
        self.company = config["company"]
        llm_cfg = dict(config["llm"])
        if batch_size:
            llm_cfg["batch_size"] = batch_size
        self.batch_size = max(1, int(llm_cfg["batch_size"]))
        self.llm = LLMClient(llm_cfg, provider, model, company_cfg=self.company)
        self.system_prompt = build_system_prompt(self.company)
        self.events: list[str] = []  # alerts surfaced in the report

    # ---------------- LLM enrichment ----------------
    def _run_batch(self, payloads: list[dict], depth: int = 0) -> dict:
        """Returns {lead_id: sanitised_result}. Never raises."""
        if not payloads:
            return {}
        ids = [p["id"] for p in payloads]
        try:
            data = self.llm.complete_json(self.system_prompt, build_user_prompt(payloads))
            items = data.get("leads", []) if isinstance(data, dict) else data
            got = {str(i.get("id")): _sanitise(i) for i in items if isinstance(i, dict) and i.get("id")}
            missing = [i for i in ids if i not in got]
            if missing:
                self.events.append(f"LLM omitted {len(missing)} lead(s) {missing} from a batch; used fallback")
            return {k: v for k, v in got.items() if k in ids}
        except CircuitOpen:
            return {}
        except LLMError as e:
            if depth == 0 and len(payloads) > 1 and not self.llm.breaker_open:
                mid = len(payloads) // 2
                self.events.append(f"Batch {ids[0]}..{ids[-1]} failed ({e}); splitting into two halves")
                log.warning("Batch of %d failed (%s) — bisecting", len(payloads), e)
                res = self._run_batch(payloads[:mid], depth + 1)
                res.update(self._run_batch(payloads[mid:], depth + 1))
                return res
            self.events.append(f"Batch {ids[0]}..{ids[-1]} failed after retries ({e}); rubric-only fallback")
            log.error("Batch %s..%s failed permanently: %s", ids[0], ids[-1], e)
            return {}

    # ---------------- main ----------------
    def run(self, csv_path: str) -> dict:
        t0 = time.time()
        leads, file_warnings = load_leads(csv_path)
        self.events.extend(file_warnings)
        as_of = resolve_as_of(self.config["rubric"].get("as_of_date", "auto"), leads)
        rubric = Rubric(self.config["rubric"], as_of)
        log.info("Analysis date (as_of) = %s", as_of)

        # Pass 1: rubric-only pre-assessment decides who needs the LLM and for what.
        pre = {l.lead_id: rubric.assess(l) for l in leads}
        jobs = []
        for l in leads:
            a = pre[l.lead_id]
            if l.duplicate_of or a.knocked_out:
                continue  # nothing the LLM could change
            # A message is only worth writing if the lead could end up qualified/review.
            could_progress = a.score_range[1] >= rubric.r_below
            jobs.append(lead_payload(l, a, rubric, write_message=could_progress))

        # Pass 2: batched LLM calls.
        llm_results: dict = {}
        batches = [jobs[i:i + self.batch_size] for i in range(0, len(jobs), self.batch_size)]
        for n, b in enumerate(batches, 1):
            if self.llm.breaker_open:
                self.events.append(f"Circuit breaker open — {sum(len(x) for x in batches[n - 1:])} remaining "
                                   "lead(s) processed rubric-only")
                log.error("Circuit breaker open; skipping %d remaining batch(es)", len(batches) - n + 1)
                break
            log.info("LLM batch %d/%d (%d leads)", n, len(batches), len(b))
            llm_results.update(self._run_batch(b))

        # Pass 3: final decision, messages, ranking.
        job_ids = {j["id"] for j in jobs}
        records = []
        for l in leads:
            r = llm_results.get(l.lead_id)
            a = rubric.assess(l, r and r["industry_tier"], r and r["industry_confidence"], r and r["risk_flags"])
            status = "ok" if r else ("fallback" if l.lead_id in job_ids else "not_needed")
            message, msg_source = None, None
            if a.decision in (QUALIFIED, REVIEW) and (l.company or l.name):
                ctx = {"name": l.name, "company": l.company, "company_size": l.company_size, "industry": l.industry,
                       "source": l.source, "days_since_last_touch": a.days_since_interaction}
                problem = validate_message(r.get("message"), ctx) if r else "no LLM result"
                if problem is None:
                    message = {**r["message"], "variant": variant_for(l.source)}
                    msg_source = "llm"
                else:
                    message = template_message(ctx, self.company)
                    msg_source = "template_fallback"
                    if r:
                        self.events.append(f"{l.lead_id}: LLM message rejected ({problem}); template used")
            if status == "fallback" and a.factors["industry"].points is None and l.industry:
                a.reasons.append("AI industry classification unavailable (API failure) — industry treated as unknown")
            records.append({"lead": l, "a": a, "llm": r, "llm_status": status,
                            "message": message, "message_source": msg_source})

        # Rank: qualified first (by score, then intent, recency, size), then review queue.
        def key(rec):
            a, l = rec["a"], rec["lead"]
            order = {QUALIFIED: 0, REVIEW: 1, REJECTED: 2}[a.decision]
            return (order, -a.score, -(a.factors["source"].points or 0), -(a.factors["recency"].points or 0),
                    -(a.factors["size"].points or 0), l.lead_id)
        records.sort(key=key)
        rank = 0
        for rec in records:
            rec["priority"], rec["sla"] = rubric.priority(rec["a"])
            if rec["a"].decision != REJECTED:
                rank += 1
                rec["rank"] = rank
            else:
                rec["rank"] = None

        return {"records": records, "as_of": as_of, "rubric": rubric, "duration_s": round(time.time() - t0, 2),
                "llm_stats": dict(self.llm.stats), "provider": self.llm.provider, "model": self.llm.model,
                "batches": len(batches), "events": self.events, "input_file": csv_path}
