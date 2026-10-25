# Lead Intelligence System

A command-line tool that scores leads against an explicit rubric and uses an LLM, in batches, for judgement calls. It ranks an outreach queue, drafts a personalised first email for each lead worth contacting, and writes a report the sales team can act on.

**Pipeline:** intake & validate → rubric pre-score → batched LLM enrichment (20 leads per call) → final decision → rank → report

## Run it
```bash
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY=...        # or GROQ_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY
python3 test_prompts.py --provider anthropic                 # sanity-check the prompt on 8 leads (1 call)
python3 main.py data/leads_full_scale_100.csv --out output/full_scale_100
python3 main.py data/leads_testing.csv --provider groq --batch-size 10 --out output/testing
python3 main.py data/leads.csv --provider mock               # offline dry run, no key needed
python3 -m unittest discover -s tests -v                     # 19 tests, no network needed
```
Each run writes `output_report.json` (full detail and stats), `output_report.csv` (one row per lead, ready for a CRM), `sales_summary.md` (a one-page brief for the team) and `run.log`.

## Qualification rubric
Each lead gets **size fit (0–2.5) + industry fit (0–2.5) + buying intent from source (0–3) + engagement recency (0–2) = up to 10 points**. Scores **≥ 7.5 qualify** (P1 if ≥ 9.0, contact within 24 h; otherwise P2, within 3 days). Scores **< 6.5 are rejected**, and **6.5–7.4 goes to human review**. Two hard knockouts override the score: **fewer than 10 employees**, or **no contact for over a year**. All weights and bands live in `config.yaml`.

**Where the LLM fits.** The rubric is deterministic, so identical leads always get identical scores and every point can be traced. The LLM does three things the rules can't:
1. Classifies industries the rubric doesn't list, with a confidence score. Below 0.6, the industry is treated as unknown.
2. Raises red flags, such as a test-looking record or a company name suggesting it has shut down.
3. Writes the email in one of three variants: *inbound follow-up*, *warm intro* or *value-first*.

A red flag can move a qualified lead to review, but the LLM can never qualify or reject a lead by itself.

**Missing data.** Each unknown factor is scored as a range from 0 to its maximum. If the decision is the same at both ends, the tool decides; if not, the lead goes to review with the reason "decision depends on missing X". A lead with no company also goes to review, because its fit can't be verified.

## Robustness
- **Retries:** exponential backoff with jitter (up to 4 attempts). The tool honours `Retry-After` on 429 responses and also retries 5xx errors, timeouts and malformed or truncated JSON. Auth and 4xx errors fail fast.
- **Failed batches:** the batch is split in half once. Any leads still unresolved get **rubric-only scoring and a template email**, labelled `llm_status: fallback` and listed under `alerts`.
- **Circuit breaker:** after 3 consecutive failed batches the tool stops calling the API, so a dead endpoint never stalls the run.
- **Throttling:** requests are paced client-side to the configured requests per minute.
- **Output checks:** each LLM email must mention the company, contain no placeholders and fall within the length limits; otherwise the template is used.
- **Bad input:** `NA`, blanks and "Unknown…" values, size ranges like `11-50`, several date formats, future dates, blank rows and duplicates are all handled. Each problem is recorded per lead in `data_issues`.
- **Evidence:** `output/failure_injection/` holds a run of all 100 leads where 35% of calls failed and 10% returned broken JSON. It made 10 retries and every decision matched the clean run.

## Results (`output/`)
| Dataset | Leads | Qualified | Review | Rejected |
|---|---|---|---|---|
| full_scale_100 (submission report, also `output_report.json`) | 100 | 49 (15 P1) | 22 | 29 |
| training | 29 | 12 | 6 | 11 |
| testing (messy) | 20 | 6 | 8 | 6 |

The most common rejection reasons are a weak-intent source (cold LinkedIn outreach or a content download), a low-fit industry and stale engagement.

## Assumptions, pivots and limitations
- **Assumed product.** The brief doesn't name the product, so I assumed "FlowPilot", a RevOps / lead-routing SaaS for 50–1,000-person B2B teams. Change the `company:` block in `config.yaml` to rebrand the emails.
- **Analysis date.** "Now" is set to the latest interaction date in the file (2024-01-20) rather than today; otherwise every lead in this Jan-2024 snapshot would count as stale. Set `as_of_date` in the config to override.
- **Pivot:** v1 weighted every factor about equally, with a 5.0–6.9 review band. It qualified 65% of leads, including cold LinkedIn contacts on fit alone, and sent 29 leads to review. Intent now carries the most weight and the band is 6.5–7.4, giving 49% qualified and 22% in review.
- **Sample reports are offline.** The reports in `output/` were generated with `--provider mock`, which follows the same JSON contract but uses keyword industry classification and template emails, because no API key was available when they were built. Re-run with a real key to get LLM-written emails; the decisions will only differ for leads in unlisted industries or ones the LLM flags.
- **Limited signals.** The rubric only sees six fields, with no budget, title or timeline. A cold enterprise lead can therefore never reach P1, which is deliberate. The email time slots are fixed placeholders rather than read from a calendar.
- **Free-tier limits.** Free tiers have token-per-minute caps; Groq's 70B model has a low one. If you hit 429s, use `--batch-size 10`. The retries cope either way; it's just slower.
