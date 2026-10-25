"""Deterministic qualification rubric.

Four factors, 10 points total (weights live in config.yaml):
    size fit (2.5) + industry fit (2.5) + source intent (3.0) + recency (2.0)

Why deterministic: the same lead must always get the same score, and every point
must be traceable to a rule a sales manager can read in config.yaml. The LLM is
used for judgement the rules can't make (classifying unfamiliar industries,
spotting red flags, writing messages) — it never sets the score directly.

Missing data: a missing factor is scored as an interval [0, factor_max]. If the
decision is the same at both ends, missing data doesn't matter and we decide. If
the decision flips, the lead goes to REVIEW ("decision depends on missing X")
instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .ingest import Lead

QUALIFIED, REVIEW, REJECTED = "qualified", "review", "rejected"


@dataclass
class FactorResult:
    factor: str
    points: Optional[float]  # None = unknown
    max_points: float
    detail: str


@dataclass
class Assessment:
    factors: dict = field(default_factory=dict)
    score: float = 1.0                 # observed score (unknown factors = 0), clamped 1-10
    score_range: tuple = (1.0, 1.0)    # (min, max) given unknowns
    decision: str = REVIEW
    reasons: list = field(default_factory=list)          # human-readable reasoning lines
    rejection_reasons: list = field(default_factory=list)  # short codes for aggregation
    review_reasons: list = field(default_factory=list)
    knocked_out: bool = False
    days_since_interaction: Optional[int] = None
    industry_tier: Optional[str] = None
    industry_tier_source: Optional[str] = None  # "rubric" | "llm" | None


class Rubric:
    def __init__(self, cfg: dict, as_of: date):
        self.cfg = cfg
        self.as_of = as_of
        t = cfg["thresholds"]
        self.q_min, self.r_below, self.p1_min = t["qualified_min"], t["rejected_below"], t["p1_min"]
        self.min_size = cfg["knockouts"]["min_company_size"]
        self.max_days = cfg["knockouts"]["max_days_since_interaction"]
        self.min_conf = cfg.get("min_industry_confidence", 0.6)
        self.industry_lookup = {}
        self.tier_points = {}
        for tier, spec in cfg["industry_tiers"].items():
            self.tier_points[tier] = spec["points"]
            for ind in spec["industries"]:
                self.industry_lookup[ind.lower()] = tier
        self.source_points = {k.lower(): v for k, v in cfg["source_points"].items()}
        # Factor maxima are derived from config so weights can be retuned without code changes.
        self.max_pts = {"size": max(b["points"] for b in cfg["size_bands"]),
                        "industry": max(self.tier_points.values()),
                        "source": max(self.source_points.values()),
                        "recency": max(b["points"] for b in cfg["recency_bands"])}

    # ---------------- individual factors ----------------
    def known_industry_tier(self, industry: Optional[str]) -> Optional[str]:
        return self.industry_lookup.get(industry.lower()) if industry else None

    def score_size(self, n: Optional[int]) -> FactorResult:
        if n is None:
            return FactorResult("size", None, self.max_pts["size"], "company size unknown")
        for b in self.cfg["size_bands"]:
            if b["min"] <= n <= b["max"]:
                return FactorResult("size", b["points"], self.max_pts["size"], f"{n} employees -> {b['label']}")
        return FactorResult("size", 0.0, self.max_pts["size"], f"{n} employees -> outside configured bands")

    def score_industry(self, lead: Lead, llm_tier: Optional[str], llm_conf: Optional[float]):
        tier = self.known_industry_tier(lead.industry)
        src = "rubric" if tier else None
        if tier is None and lead.industry and llm_tier in self.tier_points and (llm_conf or 0) >= self.min_conf:
            tier, src = llm_tier, "llm"
        if tier is None:
            why = "industry unknown" if not lead.industry else (
                f"'{lead.industry}' not in rubric and LLM classification unavailable/low-confidence")
            return FactorResult("industry", None, self.max_pts["industry"], why), None, None
        pts = self.tier_points[tier]
        note = f"'{lead.industry}' -> {tier} vertical" + (f" (LLM-classified, conf {llm_conf:.2f})" if src == "llm" else "")
        return FactorResult("industry", pts, self.max_pts["industry"], note), tier, src

    def score_source(self, source: Optional[str]) -> FactorResult:
        if source is None:
            return FactorResult("source", None, self.max_pts["source"], "lead source unknown")
        pts = self.source_points.get(source.lower())
        if pts is None:
            return FactorResult("source", None, self.max_pts["source"], f"unrecognised source '{source}'")
        return FactorResult("source", pts, self.max_pts["source"], f"{source} intent")

    def score_recency(self, d: Optional[date]) -> tuple[FactorResult, Optional[int]]:
        if d is None:
            return FactorResult("recency", None, self.max_pts["recency"], "last interaction date unknown"), None
        days = (self.as_of - d).days
        if days < 0:
            return FactorResult("recency", None, self.max_pts["recency"], f"interaction date {d} is in the future (data error)"), days
        for b in self.cfg["recency_bands"]:
            if days <= b["max_days"]:
                return FactorResult("recency", b["points"], self.max_pts["recency"], f"last touch {days}d ago -> {b['label']}"), days
        return FactorResult("recency", 0.0, self.max_pts["recency"], f"last touch {days}d ago -> stale (>1 year)"), days

    # ---------------- decision ----------------
    def _decide(self, s: float) -> str:
        if s >= self.q_min:
            return QUALIFIED
        if s < self.r_below:
            return REJECTED
        return REVIEW

    def assess(self, lead: Lead, llm_tier: Optional[str] = None, llm_conf: Optional[float] = None,
               llm_flags: Optional[list] = None) -> Assessment:
        a = Assessment()
        size = self.score_size(lead.company_size)
        ind, a.industry_tier, a.industry_tier_source = self.score_industry(lead, llm_tier, llm_conf)
        src = self.score_source(lead.source)
        rec, a.days_since_interaction = self.score_recency(lead.last_interaction_date)
        a.factors = {f.factor: f for f in (size, ind, src, rec)}

        lo = sum(f.points or 0.0 for f in a.factors.values())
        hi = sum(f.points if f.points is not None else f.max_points for f in a.factors.values())
        clamp = lambda x: round(min(10.0, max(1.0, x)), 1)
        a.score, a.score_range = clamp(lo), (clamp(lo), clamp(hi))
        for f in a.factors.values():
            pts = "?" if f.points is None else f"+{f.points:g}"
            a.reasons.append(f"{f.factor}: {pts}/{f.max_points:g} — {f.detail}")

        # 1) Duplicates are never worked twice.
        if lead.duplicate_of:
            a.decision, a.knocked_out = REJECTED, True
            a.rejection_reasons.append("duplicate record")
            a.reasons.append(f"DUPLICATE of {lead.duplicate_of}: suppressed to avoid double outreach")
            return a

        # 2) Hard knockouts (only on data we actually have).
        if lead.company_size is not None and lead.company_size < self.min_size:
            a.knocked_out = True
            a.rejection_reasons.append(f"company too small (<{self.min_size} employees)")
            a.reasons.append(f"KNOCKOUT: {lead.company_size} employees is below the {self.min_size}-person minimum "
                             "(no RevOps/sales-ops function to buy)")
        if a.days_since_interaction is not None and a.days_since_interaction > self.max_days:
            a.knocked_out = True
            a.rejection_reasons.append("stale engagement (>1 year)")
            a.reasons.append(f"KNOCKOUT: last interaction {a.days_since_interaction} days ago — "
                             "route to re-engagement nurture, not sales")
        if a.knocked_out:
            a.decision = REJECTED
            return a

        # 3) Not enough to identify/contact the lead at all.
        if not lead.company and not lead.name:
            a.decision = REVIEW
            a.review_reasons.append("no name or company — cannot contact")
            a.reasons.append("REVIEW: record has neither a contact name nor a company")
            return a

        # 4) Score-based decision with the missing-data interval.
        d_lo, d_hi = self._decide(lo), self._decide(hi)
        unknown = [f.factor for f in a.factors.values() if f.points is None]
        if d_lo == d_hi:
            a.decision = d_lo
            if unknown:
                a.reasons.append(f"Missing {', '.join(unknown)} cannot change the outcome "
                                 f"(range {a.score_range[0]}-{a.score_range[1]})")
        else:
            a.decision = REVIEW
            a.review_reasons.append(f"decision depends on missing data ({', '.join(unknown)})")
            a.reasons.append(f"REVIEW: score could be {a.score_range[0]}-{a.score_range[1]} depending on "
                             f"unknown {', '.join(unknown)} — needs a human to fill the gap")

        if a.decision == REVIEW and not a.review_reasons:
            a.review_reasons.append(f"borderline score ({self.r_below:g}-{self.q_min - 0.1:g} band)")
            a.reasons.append(f"REVIEW: {a.score} sits in the {self.r_below:g}-{self.q_min - 0.1:g} "
                             "too-close-to-call band")
        if a.decision == REJECTED:
            a.rejection_reasons.extend(self._weakest_factors(a))
            a.reasons.append(f"REJECTED: {a.score} < {self.r_below:g} threshold")
        if a.decision == QUALIFIED:
            a.reasons.append(f"QUALIFIED: {a.score} >= {self.q_min:g} threshold")

        # 5) We can't verify fit or personalise outreach without knowing the company.
        if not lead.company and a.decision == QUALIFIED:
            a.decision = REVIEW
            a.review_reasons.append("company name missing — verify account before outreach")
            a.reasons.append("REVIEW: scores as qualified but the company is unknown, so fit can't be verified")

        # 6) LLM red flags can only send a lead to human review — never auto-qualify/reject.
        high = [f for f in (llm_flags or []) if f.get("severity") == "high"]
        if high and a.decision == QUALIFIED:
            a.decision = REVIEW
            for f in high:
                a.review_reasons.append(f"AI red flag: {f.get('flag')}")
            a.reasons.append("REVIEW: rubric says qualified but the AI raised a red flag — human check before outreach")
        for f in llm_flags or []:
            a.reasons.append(f"AI note ({f.get('severity', 'low')}): {f.get('flag')}")
        return a

    def _weakest_factors(self, a: Assessment) -> list:
        """Name the factors that cost the most points — used for 'common rejection reasons'."""
        labels = {
            "size": "poor size fit", "industry": "low-fit industry",
            "source": "weak buying intent (cold source)", "recency": "engagement gone cold",
        }
        out = []
        for f in a.factors.values():
            if f.points is not None and f.points / f.max_points <= 0.4:
                out.append(labels[f.factor])
        return out or ["below threshold on combined factors"]

    def priority(self, a: Assessment) -> tuple[str, str]:
        if a.decision == QUALIFIED:
            return ("P1", "contact within 24h") if a.score >= self.p1_min else ("P2", "contact within 3 business days")
        if a.decision == REVIEW:
            return "P3-review", "human decision within 2 business days"
        return "—", "no sales outreach"
