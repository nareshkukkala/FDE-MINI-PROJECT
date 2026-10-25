# Lead qualification summary — leads.csv
Analysis date 2024-01-20 · 49 leads · model `mock/mock-deterministic` · 3 API calls in 3 batches · 0.01s

**18 qualified (36.7%)** — 8 P1, 10 P2 · **14 for review** · **17 rejected**

## Priority queue
| # | Lead | Company | Score | Priority | Source |
|---|---|---|---|---|---|
| 1 | Alice Chen | CloudScale AI | 10.0 | P1 | Inbound demo request |
| 2 | Test_RecentEngagement | Hot Lead Corp | 10.0 | P1 | Inbound demo request |
| 3 | Samuel Lee | Cybersecurity Startup | 9.5 | P1 | Referral |
| 4 | Nathan Brooks | Enterprise Solutions Corp | 9.2 | P1 | Inbound demo request |
| 5 | Test_HighValueMatch | Perfect Fit Enterprise | 9.2 | P1 | Inbound demo request |
| 6 | Jack White | Digital Marketing Agency | 9.0 | P1 | Inbound demo request |
| 7 | Test_MultipleInteractions | Active Company | 9.0 | P1 | Inbound demo request |
| 8 | Test_SMBAverage | Average SMB Co | 9.0 | P1 | Inbound demo request |
| 9 | Test_VeryLargeEnterprise | Global Fortune 500 Corp | 8.2 | P2 | Inbound demo request |
| 10 | Leon Chen | FinTech Startup | 8.2 | P2 | Referral |
| 11 | Zara Hassan | Education Institution | 8.0 | P2 | Inbound demo request |
| 12 | Victor Moore | Real Estate Platform | 8.0 | P2 | Sales call |
| 13 | Xavier Lopez | Data Analytics Firm | 8.0 | P2 | Webinar attendee |
| 14 | Henry Park | EdTech Innovations | 8.0 | P2 | Content download |
| 15 | Emma Thompson | RetailWorks Solutions | 7.5 | P2 | Inbound demo request |
| 16 | Tina Patel | Energy Solutions | 7.5 | P2 | Inbound demo request |
| 17 | Quinn Matthews | Consulting Firm | 7.5 | P2 | Webinar attendee |
| 18 | Test_WeekOldInteraction | Week Old Corp | 7.5 | P2 | Webinar attendee |

## Needs a human decision
| Lead | Company | Score (range) | Why |
|---|---|---|---|
| Test_MissingName | — | 8.0 (8.0–8.0) | company name missing — verify account before outreach |
| Test_MissingSize | Test Inc | 7.5 (7.5–10.0) | AI red flag: company name looks like test/placeholder data |
| Frank Liu | Healthcare Systems Ltd | 7.2 (7.2–7.2) | borderline score (6.5-7.4 band) |
| Test_MidMarketSoft | Mid Market Software | 7.2 (7.2–7.2) | borderline score (6.5-7.4 band) |
| Yuki Tanaka | Travel Technology | 7.0 (7.0–7.0) | borderline score (6.5-7.4 band) |
| Karen Miller | InsurancePro | 7.0 (7.0–7.0) | borderline score (6.5-7.4 band) |
| Bella Cross | Legal Services Firm | 7.0 (7.0–7.0) | borderline score (6.5-7.4 band) |
| Wendy Zhang | Fashion Brand | 6.5 (6.5–6.5) | borderline score (6.5-7.4 band) |
| Cassandra Jones | Media & Entertainment | 6.5 (6.5–6.5) | borderline score (6.5-7.4 band) |
| Test_NoSourceInfo | Source Unknown Corp | 6.0 (6.0–9.0) | decision depends on missing data (source) |
| Test_UnknownIndustry | Mysterious Startup | 5.8 (5.8–8.2) | decision depends on missing data (industry) |
| Test_MissingDate | Mystery Co | 5.0 (5.0–10.0) | decision depends on missing data (source, recency) |
| Test_PartialData | Tech Partial | 4.5 (4.5–10.0) | decision depends on missing data (size, source) |
| Test_NameOnly | James Wilson | 1.0 (1.0–10.0) | decision depends on missing data (size, industry, source, recency) |

## Top rejection reasons
- weak buying intent (cold source): 7
- company too small (<10 employees): 6
- low-fit industry: 5
- engagement gone cold: 3
- below threshold on combined factors: 1
- stale engagement (>1 year): 1

## Sample outreach
### CloudScale AI — inbound_followup (llm)
**Subject:** Your FlowPilot demo for CloudScale AI

Hi Alice,  
  
Thanks for requesting a demo earlier this week. For a team of about 50 in SaaS, the usual bottleneck is trial sign-ups and demo requests going cold before an AE ever replies, so I'd tailor the demo around how CloudScale AI could route and follow up on those automatically. With FlowPilot, teams typically cut lead response time from days to minutes.  
  
Would Tuesday at 11:00 or Thursday at 15:00 work for a 30-minute walkthrough? Happy to fit around your calendar.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### Cybersecurity Startup — warm_intro (llm)
**Subject:** Following up from mutual connection's introduction

Hi Samuel,  
  
Great to connect via a mutual connection's introduction a few weeks ago. Many Cybersecurity teams like Cybersecurity Startup (a team of about 60) tell us their biggest leak is trial sign-ups and demo requests going cold before an AE ever replies.  
  
Out of curiosity, how does Cybersecurity Startup decide today which inbound leads get a same-day reply? If it's useful, I can share how similar teams use FlowPilot — teams typically cut lead response time from days to minutes.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### EdTech Innovations — value_first (llm)
**Subject:** Faster lead follow-up at EdTech Innovations

Hi Henry,  
  
I noticed EdTech Innovations' interest in our work earlier this week. For a team of about 75 in EdTech, one pattern we see often is institutional enquiries slipping between admissions, sales and partnerships — and response time is usually the cheapest win available.  
  
FlowPilot is a revenue-operations platform that scores, routes and follows up on inbound leads automatically; teams typically cut lead response time from days to minutes. Would a two-page teardown of how that could look for EdTech Innovations be useful? No call needed unless it is.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### Hot Lead Corp — inbound_followup (llm)
**Subject:** Your FlowPilot demo for Hot Lead Corp

Hi there,  
  
Thanks for requesting a demo today. For a team of about 200 in SaaS, the usual bottleneck is trial sign-ups and demo requests going cold before an AE ever replies, so I'd tailor the demo around how Hot Lead Corp could route and follow up on those automatically. With FlowPilot, teams typically cut lead response time from days to minutes.  
  
Would Tuesday at 11:00 or Thursday at 15:00 work for a 30-minute walkthrough? Happy to fit around your calendar.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot

### FinTech Startup — warm_intro (llm)
**Subject:** Following up from mutual connection's introduction

Hi Leon,  
  
Great to connect via a mutual connection's introduction earlier this week. Many FinTech teams like FinTech Startup (a 25-person team) tell us their biggest leak is high-intent applicants waiting days for a compliant first response.  
  
Out of curiosity, how does FinTech Startup decide today which inbound leads get a same-day reply? If it's useful, I can share how similar teams use FlowPilot — teams typically cut lead response time from days to minutes.  
  
Best,  
Priya Nair  
Account Executive, FlowPilot
