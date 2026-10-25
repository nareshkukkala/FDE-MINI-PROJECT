# Mini Project Delivery - Complete Package

## What Was Delivered

This package addresses the questions raised in **Ticket #8541** (Giby James, Cohort 2, IIT Roorkee) about missing ground truth and scale gaps.

---

## 📋 Complete File List

### 1. **Mini_Project_Brief.docx** (Main Assignment Document)
   - Professional Word document format
   - Clear problem statement, deliverables, success criteria, grading rubric
   - Includes **"Project Scope Note"** clarifying M1/M2/M3 weight distribution
   - Ready to distribute to students

### 2. **leads_training.csv** (30 leads)
   - Clean, complete training dataset
   - **Purpose:** Students develop and test their rubric here
   - Mix of industries, company sizes, sources, and interaction dates
   - **NO expected outcomes** — students design their own qualification logic

### 3. **leads_full_scale_100.csv** (100 leads) ⭐ **NEW**
   - Production-scale dataset addressing the "100 leads" requirement
   - **100 leads** across **46 different industries**
   - Company sizes from 3 to 8,000 employees
   - All 6 source types represented
   - **Complete, clean data** (no edge cases)
   - **Purpose:** Students verify their system can handle full scale

### 4. **leads_testing.csv** (20 leads)
   - Messy, edge-case dataset
   - **Purpose:** Test robustness and error handling
   - Missing fields, invalid data, stale interactions
   - Students should NOT crash on this data

### 5. **DATA_README.md**
   - Guide to all three datasets
   - When to use each file
   - Recommended workflow: Train → Test → Scale
   - Column definitions and data quality expectations
   - Quick stats showing diversity

### 6. **EXPECTED_OUTCOMES_NOTE.md** ⭐ **NEW**
   - **Directly addresses Giby's concern about ground truth**
   - Clarifies that datasets have NO expected outcomes (intentional)
   - Explains that students design their own rubric
   - Shows what good scoring looks like vs. weak scoring
   - Guides grading on consistency and defensibility, not "correctness"

---

## ✅ Addressing Giby's Two Concerns

### Concern 1: "Ground Truth / Expected Outcomes Missing"

**Answer:** YES, intentionally. See **EXPECTED_OUTCOMES_NOTE.md**.

Students are NOT matching against an answer key. They are:
- Defining their own qualification rubric (3-5 factors)
- Applying it consistently
- Explaining their logic

**Grading focus:** Consistency and defensibility, not "matching expected results"

**Why?** This teaches problem-structuring (M1) — the core skill. If there were answer keys, students would just code a lookup table.

---

### Concern 2: "Scale Gap: 20 vs 100 Leads"

**Answer:** SOLVED. See **leads_full_scale_100.csv**.

**Delivered:**
- 30 leads for training
- **100 leads for production-scale validation** ← addresses the requirement
- 20 leads for edge-case testing
- **Total: 150 unique leads across 3 files**

**Workflow for students:**
1. Develop with 30 training leads
2. Validate robustness with 20 test leads (messy)
3. **Scale to 100 leads** to prove it works at intended scale
4. Submit output report from the 100-lead run

---

## 📊 Data Summary

| File | Leads | Purpose | Data Quality | Date Range |
|------|-------|---------|--------------|-----------|
| training | 30 | Development | 100% complete | Aug 2023 - Jan 2024 |
| **full_scale_100** | **100** | **Production-scale** | **100% complete** | **Dec 2023 - Jan 2024** |
| testing | 20 | Robustness | 60% complete (intentional) | Jun 2022 - Jan 2024 |
| **TOTAL** | **150** | — | — | — |

---

## 🎯 Recommended Instructor Actions

1. **Review EXPECTED_OUTCOMES_NOTE.md** — This directly answers Giby's first question
2. **Distribute all files to students** along with Mini_Project_Brief.docx
3. **Emphasize the workflow:**
   - "Start with 30 training leads"
   - "Test your code with 20 messy leads"
   - "Submit your final report using the 100 full-scale leads"
4. **Grade on:** Rubric clarity, decision consistency, error handling, not on whether they "got it right"

---

## 📝 Key Messages for Students

### From DATA_README.md
> "Recommended Workflow: Use training data to develop → Use testing data for validation → Process full-scale data to verify production readiness"

### From EXPECTED_OUTCOMES_NOTE.md
> "You won't be penalized for qualifying leads that didn't convert in real life (because you don't know that). You *will* be penalized for inconsistent logic or unexplained decisions."

---

## ✨ What This Package Provides

✅ Professional project brief (Word format)  
✅ Scalable data (30 + 100 + 20 leads across 3 difficulty levels)  
✅ Clear guidance on expected outcomes  
✅ Complete documentation for students and instructors  
✅ Addresses M1 (structuring) as primary, M2/M3 as supporting  
✅ Ready to hand to students tomorrow  

---

**Status:** READY FOR DELIVERY  
**Created:** Aug 25, 2026  
**For:** FDE Academy Cohort 2, IIT Roorkee
