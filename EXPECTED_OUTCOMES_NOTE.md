# Important: About Expected Outcomes

## Ground Truth

The data files (`leads_training.csv`, `leads_full_scale_100.csv`, `leads_testing.csv`) do **NOT** include expected outcomes (e.g., "this lead was qualified and converted" or "this lead was rejected").

**This is intentional.**

You are designing your own qualification rubric based on business logic, not matching against an answer key. Your job is to:

1. **Define what "qualified" means** for your business (e.g., "Enterprise SaaS company with recent engagement")
2. **Build a rubric** with 3–5 clear factors and scoring weights
3. **Apply your rubric consistently** across all leads
4. **Defend your decisions** in your report and README

## The Goal

We're evaluating whether you can:
- **Think strategically** about what makes a good lead
- **Structure a decision process** (not just copy an answer key)
- **Apply judgment consistently** at scale
- **Explain your logic** to a sales team

## What "Correct" Looks Like

A **good** output might look like:

```
Lead: Alice Chen, CloudScale AI (50 people, SaaS, recent inbound)
Score: 8/10
Decision: QUALIFIED
Reasoning: 
  - Company size (50) matches target SMB range (+2)
  - SaaS is core vertical (+2)
  - Recent inbound signal shows active buying interest (+2)
  - No negative signals detected (+2)
  - Total: 8/10, priority HIGH
```

A **weak** output might look like:

```
Score: 7
Decision: QUALIFIED
Reasoning: seems like a good lead
```

The difference: **explainability and consistency.**

## How You'll Be Graded

- **Correctness:** Do your scores make sense given your stated rubric?
- **Consistency:** Do you apply the same logic to similar leads?
- **Defensibility:** Can you explain why each lead got its score?
- **Clarity:** Is your rubric documented so someone else could apply it?

You won't be penalized for qualifying leads that *didn't* convert in real life (because you don't know that). You *will* be penalized for inconsistent logic or unexplained decisions.

## One More Thing

**No lead is "inherently right or wrong."** A solopreneur startup might be perfect for one business and completely wrong for another. The point is that *you* define the criteria and apply them thoughtfully.

Design your rubric. Stick to it. Explain it. That's the work.
