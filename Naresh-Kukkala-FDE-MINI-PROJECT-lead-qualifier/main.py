#!/usr/bin/env python3
"""Lead Intelligence System — CLI entry point.

Examples
    export ANTHROPIC_API_KEY=...            # or GROQ_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY
    python3 main.py data/leads_full_scale_100.csv
    python3 main.py data/leads_testing.csv --provider groq --out output/testing
    python3 main.py data/leads.csv --provider mock          # offline dry run, no key needed
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

import yaml

from lead_qualifier.pipeline import Pipeline
from lead_qualifier.report import build_report, write_outputs


def setup_logging(out_dir: str, verbose: bool):
    os.makedirs(out_dir, exist_ok=True)
    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    handlers = [logging.FileHandler(os.path.join(out_dir, "run.log"), mode="w", encoding="utf-8"),
                logging.StreamHandler(sys.stderr)]
    handlers[1].setLevel(logging.INFO if verbose else logging.WARNING)
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Auto-qualify leads, rank outreach and draft first messages.")
    p.add_argument("csv", help="input CSV (name, company, company_size, industry, source, last_interaction_date)")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--provider", help="anthropic | openai | groq | gemini | mock (overrides config)")
    p.add_argument("--model", help="model name (overrides config)")
    p.add_argument("--batch-size", type=int, help="leads per LLM call (overrides config)")
    p.add_argument("--out", default="output", help="output directory")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    setup_logging(args.out, args.verbose)
    with open(args.config, encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    try:
        pipe = Pipeline(config, args.provider, args.model, args.batch_size)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2
    try:
        result = pipe.run(args.csv)
    except (FileNotFoundError, ValueError) as e:
        print(f"Input error: {e}", file=sys.stderr)
        return 2

    report = build_report(result)
    paths = write_outputs(report, args.out)
    s, run = report["stats"], report["run"]
    print(f"\nProcessed {s['total_processed']} leads in {run['duration_seconds']}s "
          f"({run['api_calls']} API calls, {run['retries']} retries, provider={run['llm_provider']})")
    print(f"  Qualified: {s['qualified']} ({s['qualified_pct']}%)  [P1 {s['p1_count']}, P2 {s['p2_count']}]")
    print(f"  Review:    {s['review']} ({s['review_pct']}%)")
    print(f"  Rejected:  {s['rejected']} ({s['rejected_pct']}%)")
    if s["common_rejection_reasons"]:
        print("  Top rejection reasons: " + "; ".join(f"{r} ({c})" for r, c in s["common_rejection_reasons"][:3]))
    for a in report["alerts"][:5]:
        print(f"  ALERT: {a}")
    print("\nOutputs:\n  " + "\n  ".join(paths.values()) + f"\n  {os.path.join(args.out, 'run.log')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
