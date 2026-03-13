# Backend Analysis & Backup - February 14, 2026

## 📋 What Was Done

### 1. ✅ Complete Backup Created

All backend components have been backed up to preserve the working API:

```
✅ api/ → api_v1_backup/
✅ services/ → services_v1_backup/
✅ engine/ → engine_v1_backup/
✅ main.py → main_v1_backup.py
```

**The current API continues to work with existing frontend calls.**

---

### 2. 🔍 Critical Issues Identified

A comprehensive analysis has identified **4 calculation issues**, with one being **CRITICAL**:

#### 🔴 CRITICAL: No Income Accumulation
- **Impact:** Simulations fail for users with positive cash flow
- **Who's affected:** Anyone earning more than they spend
- **Root cause:** Surplus income is calculated but never added to accounts
- **Example:** $200k income - $50k spending = $150k surplus → **$0 saved** ❌

#### 🟡 HIGH: No 401k Contribution Modeling
- Missing employee contributions
- Missing employer matching
- Underestimates retirement readiness

#### 🟡 MEDIUM: Tax Timing Issue
- Treats taxes as withdrawn from savings
- Should be paid from current income

#### 🟢 LOW: No One-Time Contributions
- Can't model inheritance, bonuses, etc.

---

## 📚 Documentation Created

### For Quick Reference:
- **`ISSUES_QUICK_REFERENCE.md`** - One-page summary with visual diagrams

### For Detailed Analysis:
- **`CALCULATION_ISSUES_ANALYSIS.md`** - Complete analysis with:
  - Evidence and test results
  - Impact assessment
  - Root cause analysis
  - Recommended fixes
  - Priority recommendations

### For Implementation:
- **`IMPLEMENTATION_GUIDE.md`** - Step-by-step fix guide with:
  - Exact code changes needed
  - Schema updates
  - Test cases
  - Rollback plan

### For Testing:
- **`test_scenario_analysis.py`** - Automated tests that demonstrate the issues

---

## 🎯 Next Steps

### Immediate (Do This First)
1. **Review** `ISSUES_QUICK_REFERENCE.md` for overview
2. **Run test** to see the issue: `python test_scenario_analysis.py`
3. **Decide** which fix approach to take (simple vs. comprehensive)

### Short-term (This Week)
4. **Implement** the surplus accumulation fix
5. **Add tests** for accumulation scenarios
6. **Validate** against existing functionality

### Long-term (Next Month)
7. Add 401k contribution modeling
8. Update frontend to expose new parameters
9. Add user education materials

---

## 🔬 How to Reproduce the Issue

### Quick Test
```bash
cd piumal_one/tax-pensions-backend
python test_scenario_analysis.py
```

Look for output like:
```
⚠️ ISSUE: We have surplus of $140,000 but it's not being added to accounts!
```

### Manual Test via API
```bash
# Start the backend
python main.py

# In another terminal, test with curl or Postman:
POST http://localhost:5050/api/run-simulation
Content-Type: application/json

{
  "p1_start_age": 30,
  "p2_start_age": 30,
  "end_simulation_age": 40,
  "p1_employment_income": 150000,
  "p2_employment_income": 150000,
  "annual_spend_goal": 60000,
  "bal_taxable": 50000,
  ...
}
```

Check the results - taxable balance should grow by ~$150k/year but doesn't.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────┐
│  Frontend (React/TypeScript)             │
│  Port: 5173 (dev)                        │
└──────────────┬──────────────────────────┘
               │
               │ HTTP: /api/run-simulation
               │
┌──────────────▼──────────────────────────┐
│  FastAPI Backend                         │
│  main.py → api/ → services/ → engine/    │
│  Port: 5050                              │
│                                          │
│  ✅ Working: Withdrawal strategies       │
│  ✅ Working: Tax calculations            │
│  ✅ Working: RMD logic                   │
│  ✅ Working: Mortgage/real estate        │
│  ❌ Missing: Income accumulation         │
│  ❌ Missing: 401k contributions          │
└──────────────────────────────────────────┘
```

---

## 📊 Test Results Summary

### Test 1: High Income, Low Spending
- **Input:** $270k income, $60k spending, $50k starting balance
- **Expected:** ~$1.5M after 10 years
- **Actual:** ~$100k after 10 years
- **Missing:** ~$1.4M in contributions

### Test 2: Simplified Math (0% growth)
- **Input:** $200k income, $50k spending, $10k starting balance
- **Expected:** $10k + $110k/year surplus
- **Actual:** $10k (unchanged every year)
- **Conclusion:** Surplus is never accumulated

---

## 🎓 Key Learnings

### What Works Well ✅
- Withdrawal strategies are sophisticated
- Tax calculations are accurate
- Real estate/mortgage modeling is comprehensive
- Code is well-organized (layered architecture)

### What Needs Improvement ⚠️
- **Assumption:** Code assumes users are always in retirement (decumulation)
- **Reality:** Many users are in accumulation phase (working years)
- **Solution:** Need to model both phases

### Why This Happened
The original implementation was designed for retirees:
- Focus on withdrawal strategies
- Focus on RMD compliance
- Focus on tax optimization in retirement

But users want to use it for:
- Retirement planning (pre-retirement)
- Wealth accumulation projections
- Contribution strategy optimization

---

## 💡 Design Decisions Needed

### Question 1: Where Should Surplus Go?
- Option A: All to taxable account (simple)
- Option B: Model 401k contributions explicitly (accurate)
- Option C: Let user specify split (flexible)

**Recommendation:** Start with Option A, add Option B in phase 2

### Question 2: How to Handle Existing Users?
- Default values for new parameters?
- Show warning if in accumulation phase?
- Auto-detect mode based on employment income?

**Recommendation:** Use sensible defaults (15% 401k, 5% match)

### Question 3: Frontend Changes?
- New section for "Contribution Settings"?
- Toggle between "Working" and "Retired" mode?
- Advanced/Simple toggle?

**Recommendation:** Start with simple toggle, add advanced in phase 2

---

## 📞 Contact & Questions

For questions about this analysis:
1. Review the documentation files
2. Run the test scenarios
3. Check the code comments in the backup

---

## 🔐 Backup Information

**Backup Date:** February 14, 2026  
**Backup Location:** Same directory as source files  
**Naming Convention:** `*_v1_backup/` and `*_v1_backup.py`

**To restore original code:**
```bash
# If needed, restore from backup
cp -r api_v1_backup/* api/
cp -r services_v1_backup/* services/
cp -r engine_v1_backup/* engine/
cp main_v1_backup.py main.py
```

**Git status:** All changes tracked in git (see git log)

---

## 📁 File Index

| File | Purpose | Read This If... |
|------|---------|----------------|
| `ISSUES_QUICK_REFERENCE.md` | One-page overview | You want a quick summary |
| `CALCULATION_ISSUES_ANALYSIS.md` | Detailed analysis | You need full details |
| `IMPLEMENTATION_GUIDE.md` | Step-by-step fixes | You're implementing the fix |
| `test_scenario_analysis.py` | Automated tests | You want to see the bug |
| `*_v1_backup/` | Original code | You need to rollback |

---

**Last Updated:** February 14, 2026  
**Analysis By:** AI Assistant  
**Status:** ✅ Analysis Complete | ⏳ Implementation Pending
