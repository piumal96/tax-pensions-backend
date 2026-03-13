# Quick Reference: Calculation Issues

## 🔴 CRITICAL ISSUE: No Income Accumulation

### The Problem (In Simple Terms)

**Current Behavior:**
```
You earn:   $200,000/year
You spend:   $50,000/year
You save:        $0/year ← WRONG!
```

**Expected Behavior:**
```
You earn:   $200,000/year
You spend:   $50,000/year
Taxes:       $40,000/year
You save:   $110,000/year ← This should happen!
```

### Visual Flow Chart

```
CURRENT IMPLEMENTATION:
┌─────────────┐
│  Income     │ $200k
│  (Employment)│
└──────┬──────┘
       │
       ├──────> Used for calculations
       │
       └──────> ❌ Never added to accounts!
       
┌─────────────┐
│  Accounts   │ $10k
│  (Taxable)  │
└──────┬──────┘
       │
       └──────> Still $10k next year!


CORRECT IMPLEMENTATION:
┌─────────────┐
│  Income     │ $200k
└──────┬──────┘
       │
       ├──────> Cover expenses ($50k)
       ├──────> Pay taxes ($40k)
       │
       └──────> Add surplus ($110k) ✅
                        ↓
              ┌─────────────┐
              │  Accounts   │ $10k → $120k
              │  (Taxable)  │
              └─────────────┘
```

---

## 🎯 Where's the Bug?

### File: `engine/core.py`

**Lines 139-349:** Main simulation loop

**Missing Logic Around Line 289:**
```python
# Current code ends withdrawal section
# Then immediately jumps to tax calculation

# MISSING: Code to handle positive cash flow!
# Should have something like:

surplus = total_income - cash_need
if surplus > 0:
    # Add surplus to accounts
    b_taxable += surplus  # After accounting for taxes
```

---

## 📊 Impact Examples

### Scenario 1: Young Professional
```
Input:
  Age: 30
  Income: $150,000
  Spending: $60,000
  Starting savings: $50,000

Expected after 10 years: ~$1.5M
Actual after 10 years: ~$100k (just market growth)

Missing: ~$1.4M in contributions!
```

### Scenario 2: Pre-Retirement
```
Input:
  Age: 55
  Income: $200,000
  Spending: $80,000
  Starting savings: $500,000

Expected after 10 years: ~$2.5M
Actual after 10 years: ~$1.0M

Missing: ~$1.5M in contributions!
```

---

## 🔧 Quick Test

Run this command to see the issue:
```bash
python test_scenario_analysis.py
```

Look for lines like:
```
⚠️ ISSUE: We have surplus of $140,000 but it's not being added to accounts!
```

---

## 📋 Checklist for Fix

- [ ] Add surplus calculation after withdrawal logic
- [ ] Add surplus to appropriate account (taxable by default)
- [ ] Account for taxes on the surplus
- [ ] Add parameters for 401k contribution rates
- [ ] Model employer 401k matching
- [ ] Update tests to verify accumulation works
- [ ] Update frontend to show contribution inputs
- [ ] Add documentation for accumulation phase

---

## 🚦 Issue Status

| Issue | Severity | Status | Priority |
|-------|----------|--------|----------|
| No surplus accumulation | 🔴 Critical | Identified | P0 - Immediate |
| No 401k contributions | 🟡 High | Identified | P1 - Week 2 |
| Tax timing problem | 🟡 Medium | Identified | P2 - Week 3 |
| No one-time contributions | 🟢 Low | Identified | P3 - Future |

---

## 💬 For Discussion

1. **Should surplus go to taxable or retirement accounts?**
   - Default to taxable?
   - Let user specify split?
   - Model 401k contributions separately?

2. **How to handle 401k contributions?**
   - Add as percentage of income?
   - Add as fixed dollar amount?
   - Model both employee + employer match?

3. **Backwards compatibility?**
   - How do existing scenarios work with new logic?
   - Need migration script?
   - Version the API?

---

**See full analysis:** `CALCULATION_ISSUES_ANALYSIS.md`
