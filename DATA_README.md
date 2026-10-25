# Lead Qualification Project - Data Files

This directory contains sample training and testing data for the Lead Intelligence System mini project.

## Files

### `leads_training.csv`
**Purpose:** Primary training dataset for development and prototyping.

- **30 leads** with diverse characteristics
- **Mix of scenarios:** Obvious wins, obvious rejects, and ambiguous cases
- **Industries covered:** SaaS, Finance, Healthcare, Manufacturing, Retail, Logistics, EdTech, FinTech, and more
- **Company sizes:** Startup (1-10), SMB (11-500), Mid-market (501-5000), Enterprise (5000+)
- **Sources:** Inbound demo requests, LinkedIn outreach, referrals, webinar attendees, content downloads, sales calls
- **Interaction recency:** From ~1 month ago to over 1 year ago
- **Data completeness:** All fields populated
- **Expected outcomes:** NONE. These leads have no "ground truth." You design your rubric and decide which to qualify.

**Use this to:**
- Develop your qualification rubric
- Test your LLM prompts on a small, manageable set
- Validate your scoring logic before scaling
- Iterate quickly on your approach

### `leads_full_scale_100.csv`
**Purpose:** Production-scale dataset for demonstrating your system handles 100+ leads.

- **100 leads** with realistic variety
- **Full coverage of:**
  - 30+ different industries (SaaS, Finance, Healthcare, Retail, Logistics, Energy, etc.)
  - All company size ranges (1-person solopreneurs to 8000+ enterprises)
  - All source types (inbound, LinkedIn, referrals, webinars, content downloads, sales calls)
  - Interaction dates spanning 2 months (recent and slightly aged)
- **Data completeness:** All fields populated, clean data
- **Expected outcomes:** NONE. Same as training—you qualify them based on your rubric.

**Use this to:**
- Verify your system can process 100+ leads end-to-end
- Test batch processing efficiency
- Generate your final output report
- Demonstrate scalability to the sales team

### `leads_testing.csv`
**Purpose:** Edge-case and robustness testing dataset.

- **20 leads** with deliberate messiness and edge cases
- **Problems included:**
  - Missing fields (company_size, last_interaction_date, source)
  - Missing names
  - Unknown/unmapped categories
  - Extreme company sizes (1 person, 50,000+ employees)
  - Stale interactions (over 1 year old, from 2022)
  - Very recent interactions (same day as processing)
  - Invalid or sparse data
- **Goal:** Test error handling, graceful degradation, and edge-case detection

**Use this to:**
- Test robustness of your data validation
- Verify error handling and logging
- Ensure your system flags unclear cases for human review
- Check that missing data doesn't crash the pipeline
- Build confidence in your system before going to production

## Column Definitions

| Column | Description | Example |
|--------|-------------|---------|
| `name` | Contact name | "Alice Chen" |
| `company` | Company name | "CloudScale AI" |
| `company_size` | Number of employees | 50, or "NA" if unknown |
| `industry` | Business industry | "SaaS", "Healthcare", "Retail" |
| `source` | How lead was acquired | "Inbound demo request", "LinkedIn outreach", "Referral" |
| `last_interaction_date` | Last time we touched base | "2024-01-15" (YYYY-MM-DD) or blank |

## How to Use

1. **Start with training data:** Use `leads_training.csv` to build and refine your system.
2. **Test with full dataset:** Combine both files or run them separately to validate at scale.
3. **Expect messiness in testing data:** The testing file is deliberately imperfect. Your system should handle it gracefully.
4. **Don't hardcode expectations:** Build logic that adapts to real-world data quality issues.

## Notes

- Dates are in `YYYY-MM-DD` format
- Blank/empty cells represent missing data (not the string "NA")
- Company sizes are approximate; use ranges in your rubric
- Sources may vary beyond these examples in production
- Consider your rubric's tolerance for missing data per field

## Quick Stats

**Training Data (`leads_training.csv`):**
- Total leads: 30
- Complete records: 30 (100%)
- Date range: 2023-08-30 to 2024-01-20
- Industries: 20+ different sectors
- **Purpose:** Development and iteration

**Production-Scale Data (`leads_full_scale_100.csv`):**
- Total leads: 100
- Complete records: 100 (100%)
- Date range: 2023-12-05 to 2024-01-20
- Industries: 30+ different sectors
- Company sizes: 28 (solopreneur) to 8000+ (enterprise)
- **Purpose:** Demonstrate scalability to 100+ leads

**Testing Data (`leads_testing.csv`):**
- Total leads: 20
- Complete records: ~12 (60%)
- Incomplete/edge cases: ~8 (40%)
- Date range: 2022-06-15 to 2024-01-20
- **Intentional problems:** Missing names, sizes, dates, sources; extreme values; stale interactions
- **Purpose:** Robustness and error handling validation

## Recommended Workflow

1. **Start small:** Use `leads_training.csv` (30 leads) to design and test your rubric
2. **Validate edge cases:** Run `leads_testing.csv` (20 leads) to check error handling
3. **Scale up:** Process `leads_full_scale_100.csv` (100 leads) to verify production readiness
4. **Submit:** Include output report from the 100-lead run in your final deliverable
