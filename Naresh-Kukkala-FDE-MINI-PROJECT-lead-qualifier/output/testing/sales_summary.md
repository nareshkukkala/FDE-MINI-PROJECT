# Lead qualification summary — leads_testing.csv
Analysis date 2024-01-20 · 20 leads · model `mock/mock-deterministic` · 1 API calls in 1 batches · 0.0s

**6 qualified (30.0%)** — 4 P1, 2 P2 · **8 for review** · **6 rejected**

## Priority queue
| # | Lead | Company | Score | Priority | Source |
|---|---|---|---|---|---|
| 1 | Test_RecentEngagement | Hot Lead Corp | 10.0 | P1 | Inbound demo request |
| 2 | Test_HighValueMatch | Perfect Fit Enterprise | 9.2 | P1 | Inbound demo request |
| 3 | Test_MultipleInteractions | Active Company | 9.0 | P1 | Inbound demo request |
| 4 | Test_SMBAverage | Average SMB Co | 9.0 | P1 | Inbound demo request |
| 5 | Test_VeryLargeEnterprise | Global Fortune 500 Corp | 8.2 | P2 | Inbound demo request |
| 6 | Test_WeekOldInteraction | Week Old Corp | 7.5 | P2 | Webinar attendee |

## Needs a human decision
| Lead | Company | Score (range) | Why |
|---|---|---|---|
| Test_MissingName | — | 8.0 (8.0–8.0) | company name missing — verify account before outreach |
| Test_MissingSize | Test Inc | 7.5 (7.5–10.0) | AI red flag: company name looks like test/placeholder data |
| Test_MidMarketSoft | Mid Market Software | 7.2 (7.2–7.2) | borderline score (6.5-7.4 band) |
| Test_NoSourceInfo | Source Unknown Corp | 6.0 (6.0–9.0) | decision depends on missing data (source) |
| Test_UnknownIndustry | Mysterious Startup | 5.8 (5.8–8.2) | decision depends on missing data (industry) |
| Test_MissingDate | Mystery Co | 5.0 (5.0–10.0) | decision depends on missing data (source, recency) |
| Test_PartialData | Tech Partial | 4.5 (4.5–10.0) | decision depends on missing data (size, source) |
| Test_NameOnly | James Wilson | 1.0 (1.0–10.0) | decision depends on missing data (size, industry, source, recency) |

## Top rejection reasons
- company too small (<10 employees): 4
- low-fit industry: 1
- stale engagement (>1 year): 1

## Sample outreach
### Hot Lead Corp — inbound_followup (llm)
**Subject:** Your FlowPilot demo for Hot Lead Corp

Hi there,  
  
Thanks for requesting a demo today. For a team of about 200 in SaaS, the usual bottleneck is trial sign-ups and demo requests going cold before an AE ever replies, so I'd tailor the demo around how Hot Lead Corp could route and follow up on those automatically. With FlowPilot, teams typically cut lead response time from days to minutes.  
  
Would Tuesday at 11:00 or Thursday at 15:00 work for a 30-minute walkthrough? Happy to fit around your calendar.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### Week Old Corp — warm_intro (llm)
**Subject:** Following up from the webinar

Hi there,  
  
Great to connect via the webinar earlier this week. Many Logistics teams like Week Old Corp (a team of about 250) tell us their biggest leak is RFQs and distributor enquiries routed by hand across regions.  
  
Out of curiosity, how does Week Old Corp decide today which inbound leads get a same-day reply? If it's useful, I can share how similar teams use FlowPilot — teams typically cut lead response time from days to minutes.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### Perfect Fit Enterprise — inbound_followup (llm)
**Subject:** Your FlowPilot demo for Perfect Fit Enterprise

Hi there,  
  
Thanks for requesting a demo today. For an organisation of 2,000 people in SaaS, the usual bottleneck is trial sign-ups and demo requests going cold before an AE ever replies, so I'd tailor the demo around how Perfect Fit Enterprise could route and follow up on those automatically. With FlowPilot, teams typically cut lead response time from days to minutes.  
  
Would Tuesday at 11:00 or Thursday at 15:00 work for a 30-minute walkthrough? Happy to fit around your calendar.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### Active Company — inbound_followup (llm)
**Subject:** Your FlowPilot demo for Active Company

Hi there,  
  
Thanks for requesting a demo today. For a team of about 500 in Finance, the usual bottleneck is high-intent applicants waiting days for a compliant first response, so I'd tailor the demo around how Active Company could route and follow up on those automatically. With FlowPilot, teams typically cut lead response time from days to minutes.  
  
Would Tuesday at 11:00 or Thursday at 15:00 work for a 30-minute walkthrough? Happy to fit around your calendar.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### Average SMB Co — inbound_followup (llm)
**Subject:** Your FlowPilot demo for Average SMB Co

Hi there,  
  
Thanks for requesting a demo today. For a team of about 120 in Retail, the usual bottleneck is wholesale and partnership enquiries mixed in with customer-service tickets, so I'd tailor the demo around how Average SMB Co could route and follow up on those automatically. With FlowPilot, teams typically cut lead response time from days to minutes.  
  
Would Tuesday at 11:00 or Thursday at 15:00 work for a 30-minute walkthrough? Happy to fit around your calendar.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot
