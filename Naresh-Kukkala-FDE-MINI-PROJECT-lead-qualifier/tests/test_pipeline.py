"""Run: python3 -m unittest discover -s tests -v   (no API key or network needed)"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lead_qualifier import llm as llm_mod  # noqa: E402
from lead_qualifier.ingest import Lead, load_leads, parse_size  # noqa: E402
from lead_qualifier.llm import LLMClient, LLMError, extract_json  # noqa: E402
from lead_qualifier.pipeline import Pipeline  # noqa: E402
from lead_qualifier.report import build_report  # noqa: E402
from lead_qualifier.rubric import Rubric  # noqa: E402

CFG = yaml.safe_load(open(os.path.join(ROOT, "config.yaml")))
DATA = os.path.join(ROOT, "data")


def mk(**kw):
    base = dict(lead_id="L0001", row_number=2, raw={}, name="Ana Ruiz", company="Acme Cloud", company_size=200,
                industry="SaaS", source="Inbound demo request", last_interaction_date=date(2024, 1, 18))
    base.update(kw)
    return Lead(**base)


class TestIngest(unittest.TestCase):
    def test_size_parsing(self):
        self.assertEqual(parse_size("1,200")[0], 1200)
        self.assertEqual(parse_size("11-50")[0], 30)
        self.assertEqual(parse_size("5k")[0], 5000)
        self.assertIsNone(parse_size("NA")[0])
        self.assertIsNone(parse_size("lots")[0])

    def test_messy_file_loads_without_crash(self):
        leads, _ = load_leads(os.path.join(DATA, "leads_testing.csv"))
        self.assertEqual(len(leads), 20)
        name_only = next(l for l in leads if l.company == "James Wilson")
        self.assertIsNone(name_only.industry)
        self.assertIsNone(name_only.last_interaction_date)
        unknown = next(l for l in leads if l.company == "Source Unknown Corp")
        self.assertIsNone(unknown.source)

    def test_duplicates_and_blank_rows(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write("name,company,company_size,industry,source,last_interaction_date\n"
                     "A B,Co,100,SaaS,Referral,2024-01-01\n,,,,,\nA B,Co,100,SaaS,Referral,2024-01-01\n")
        leads, warnings = load_leads(fh.name)
        self.assertEqual(len(leads), 2)
        self.assertEqual(leads[1].duplicate_of, "L0001")
        self.assertTrue(any("blank" in w for w in warnings))


class TestRubric(unittest.TestCase):
    def setUp(self):
        self.r = Rubric(CFG["rubric"], date(2024, 1, 20))

    def test_ideal_lead_qualifies(self):
        a = self.r.assess(mk())
        self.assertEqual(a.decision, "qualified")
        self.assertEqual(a.score, 10.0)

    def test_consistency_same_input_same_output(self):
        self.assertEqual(self.r.assess(mk()).score, self.r.assess(mk(lead_id="L9")).score)

    def test_knockouts(self):
        self.assertEqual(self.r.assess(mk(company_size=3)).decision, "rejected")
        self.assertEqual(self.r.assess(mk(last_interaction_date=date(2022, 6, 15))).decision, "rejected")

    def test_missing_data_that_matters_goes_to_review(self):
        a = self.r.assess(mk(source=None, industry="Retail", company_size=300,
                             last_interaction_date=date(2024, 1, 1)))
        self.assertEqual(a.decision, "review")
        self.assertIn("missing", a.review_reasons[0])

    def test_missing_data_that_cannot_matter_is_decided(self):
        a = self.r.assess(mk(industry=None))  # 7.5 even with industry=0
        self.assertEqual(a.decision, "qualified")

    def test_llm_flag_can_only_send_to_review(self):
        flags = [{"flag": "looks like test data", "severity": "high"}]
        self.assertEqual(self.r.assess(mk(), llm_flags=flags).decision, "review")
        weak = mk(company_size=20, industry="Hospitality", source="LinkedIn outreach")
        self.assertEqual(self.r.assess(weak, llm_flags=flags).decision, "rejected")

    def test_llm_industry_tier_used_only_when_confident(self):
        lead = mk(industry="Quantum Widgets")
        self.assertEqual(self.r.assess(lead, "core", 0.9).industry_tier_source, "llm")
        self.assertIsNone(self.r.assess(lead, "core", 0.3).industry_tier)

    def test_future_date_is_flagged_not_scored(self):
        a = self.r.assess(mk(last_interaction_date=date(2024, 3, 1)))
        self.assertIsNone(a.factors["recency"].points)


class FakeResp:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class TestLLMClient(unittest.TestCase):
    def client(self):
        cfg = dict(CFG["llm"], backoff_base_seconds=0.01, requests_per_minute=10000)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            return LLMClient(cfg, "anthropic")

    def test_extract_json_tolerates_fences_and_prose(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('Here you go: {"a": [1]} thanks'), {"a": [1]})

    def test_retries_429_then_5xx_then_succeeds(self):
        ok = FakeResp(200, {"content": [{"type": "text", "text": '{"leads": []}'}], "stop_reason": "end_turn"})
        seq = [FakeResp(429, headers={"retry-after": "0"}), FakeResp(503), ok]
        c = self.client()
        with mock.patch.object(llm_mod.requests, "post", side_effect=seq):
            self.assertEqual(c.complete_json("s", "u"), {"leads": []})
        self.assertEqual(c.stats["retries"], 2)
        self.assertEqual(c.stats["rate_limited"], 1)

    def test_auth_error_is_not_retried(self):
        c = self.client()
        with mock.patch.object(llm_mod.requests, "post", return_value=FakeResp(401)) as p:
            with self.assertRaises(LLMError):
                c.complete_json("s", "u")
        self.assertEqual(p.call_count, 1)

    def test_missing_key_gives_clear_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                LLMClient(CFG["llm"], "groq")


class TestPipelineResilience(unittest.TestCase):
    def run_pipe(self, csv="leads_full_scale_100.csv", env=None, **llm_overrides):
        cfg = json.loads(json.dumps(CFG))
        cfg["llm"].update(backoff_base_seconds=0.01, **llm_overrides)
        with mock.patch.dict(os.environ, env or {}):
            pipe = Pipeline(cfg, provider="mock")
            return build_report(pipe.run(os.path.join(DATA, csv)))

    def test_100_leads_batched(self):
        rep = self.run_pipe()
        self.assertEqual(rep["stats"]["total_processed"], 100)
        self.assertLessEqual(rep["run"]["api_calls"], 6)  # 100 leads / 20 per batch, not 100 calls
        for l in rep["leads"]:
            self.assertIn(l["decision"], ("qualified", "review", "rejected"))
            self.assertTrue(l["reasoning"])
            if l["decision"] == "qualified":
                self.assertIn(l["company"], l["outreach_message"]["body"])

    def test_dead_api_falls_back_and_never_crashes(self):
        rep = self.run_pipe(env={"MOCK_FAIL_RATE": "1.0"}, max_retries=1)
        self.assertEqual(rep["stats"]["total_processed"], 100)
        self.assertGreater(rep["run"]["leads_rubric_only_fallback"], 0)
        self.assertTrue(any("Circuit breaker" in a for a in rep["alerts"]))
        q = [l for l in rep["leads"] if l["decision"] == "qualified"]
        self.assertTrue(q and all(l["message_source"] == "template_fallback" for l in q))

    def test_malformed_json_is_retried(self):
        rep = self.run_pipe(env={"MOCK_MALFORMED_RATE": "0.4", "MOCK_SEED": "3"})
        self.assertGreater(rep["run"]["retries"], 0)
        self.assertEqual(rep["stats"]["total_processed"], 100)

    def test_messy_testing_file(self):
        rep = self.run_pipe("leads_testing.csv")
        self.assertEqual(rep["stats"]["total_processed"], 20)
        self.assertGreater(rep["stats"]["review"], 0)


if __name__ == "__main__":
    unittest.main()
