# Retirement Planner Backend - Calculation Issues Analysis

**Date:** February 14, 2026  
**Analyst:** AI Assistant  
**Status:** ✅ Backup Created | 🔍 Issues Identified

---

## Executive Summary

The retirement planner backend has been successfully backed up. A critical calculation flaw has been identified that causes simulations to fail even when users have positive cash flow (high income, low spending, small savings).

**CRITICAL ISSUE:** Employment income surpluses are not being added to any account balances. The engine treats income as a flow variable but never accumulates it.

---

## 🔄 Backup Status

All backend components have been successfully backed up:

- ✅ `api/` → `api_v1_backup/`
- ✅ `services/` → `services_v1_backup/`
- ✅ `engine/` → `engine_v1_backup/`
- ✅ `main.py` → `main_v1_backup.py`

The current API endpoints continue to work with the existing code.

---

## 🐛 Critical Issues Identified

### **Issue #1: Employment Income Not Accumulated (CRITICAL)**

**Severity:** 🔴 CRITICAL  
**Impact:** Simulations fail for users in accumulation phase  
**Location:** `engine/core.py` - `run_deterministic()` function

#### Problem Description

When a user has employment income that exceeds their spending needs, the surplus is not added to any account. The current implementation:

1. ✅ Calculates employment income correctly
2. ✅ Calculates total income correctly  
3. ✅ Identifies surplus correctly
4. ❌ **NEVER adds surplus to account balances**

#### Evidence

Test scenario:
- **Combined Income:** $200,000/year
- **Spending:** $50,000/year
- **Taxes:** ~$26,340/year
- **Expected Surplus:** ~$123,660/year
- **Actual Balance Change:** $0

```
Year 2026:
  Income: $200,000
  Cash Need: $60,000 (spending + taxes)
  Surplus: $140,000
  Taxable Balance: $10,000  ← Should be ~$150,000!

Year 2027:
  Income: $200,000
  Cash Need: $76,340
  Surplus: $123,660
  Taxable Balance: $10,000  ← Still $10,000! No accumulation!
```

#### Root Cause

In `engine/core.py`, lines 246-288, the code:
- Calculates `cash_need` (spending + taxes)
- Determines withdrawals when `shortfall > 0`
- **But has no logic to ADD surplus to accounts when income exceeds needs**

The simulation assumes you're always in the **decumulation phase** (retirement), never the **accumulation phase** (working years).

#### Affected Scenarios

- ❌ Young professionals starting retirement planning
- ❌ Mid-career individuals with growing accounts
- ❌ Anyone earning more than they spend
- ✅ Retirees only drawing down (works correctly)

---

### **Issue #2: 401k Contributions Not Modeled**

**Severity:** 🟡 HIGH  
**Impact:** Underestimates retirement account growth  
**Location:** `engine/core.py` - missing functionality

#### Problem Description

During working years (before retirement), the simulation doesn't account for:
- Employee 401k contributions (typically 10-20% of salary)
- Employer 401k matching (typically 3-6% of salary)
- Automatic contribution to pretax or Roth accounts

#### Example

A person earning $150,000 with:
- 15% employee contribution = $22,500/year → PreTax/Roth account
- 5% employer match = $7,500/year → PreTax/Roth account
- Total: $30,000/year that should grow tax-deferred

Currently: **$0 is being added to retirement accounts during working years**

#### Impact

This causes:
- Significant underestimation of retirement readiness
- False "simulation failed" warnings
- Unrealistic retirement account projections

---

### **Issue #3: Tax Calculation Timing Issue**

**Severity:** 🟡 MEDIUM  
**Impact:** Cash flow mismatch causes early account depletion  
**Location:** `engine/core.py`, line 246

#### Problem Description

Current logic:
```python
cash_need = spend_goal + total_mortgage_payment + previous_year_taxes
```

This creates a **tax timing problem**:
- Year 1: Earn $200k, spend $50k, owe $40k in taxes
- Year 2: Must pay $40k from last year + $50k spending = $90k cash need
- But you earned $200k in Year 2 (available to pay Year 1 taxes)

The current implementation treats taxes as if they're paid from savings, not from current income.

#### Real-World Behavior

In reality:
- Taxes are withheld from paycheck throughout the year
- Or estimated taxes are paid quarterly from current income
- Taxes are NOT paid by liquidating investment accounts

#### Impact

- Artificially inflates cash withdrawals
- Depletes accounts unnecessarily
- Especially problematic in early years with small balances

---

### **Issue #4: No Contribution Logic After Employment**

**Severity:** 🟢 LOW  
**Impact:** Minor - affects specific scenarios  
**Location:** `engine/core.py`

#### Problem Description

The system has no way to model:
- One-time contributions (inheritance, windfall)
- Post-employment consulting income
- Part-time work in semi-retirement
- Other income that should be added to accounts

---

## 📊 Test Results Summary

### Test 1: High Income, Low Spending, Small Savings

**Input:**
- Ages: 30 & 28
- Combined Income: $270,000
- Spending: $60,000
- Starting Balance: $50,000 taxable + $180,000 retirement

**Expected Behavior:**
- Should accumulate ~$150k-180k per year (after taxes)
- Should have ~$1.5M+ after 10 years
- Should easily reach retirement

**Actual Results:**
- ✅ Simulation completes (doesn't crash)
- ⚠️ Taxable account growth is MINIMAL
  - Year 1: $53,500 (+$3,500 from market, not from savings)
  - Year 2: $57,245 (+$3,745 from market, not from savings)
  - Year 10: $98,358 (purely from 7% market growth, no contributions)
- ❌ Missing ~$1.4M+ that should have been saved

### Test 2: Zero Growth, Simplified Math

**Input:**
- Income: $200,000/year
- Spending: $50,000/year
- Taxes: ~$26,340/year
- Starting Balance: $10,000
- Growth Rate: 0% (for easy math)

**Expected:**
- Year 1: $10k + ($200k - $50k - $26k) = ~$134k
- Year 2: $134k + $124k = ~$258k

**Actual:**
- Year 1: $10,000 ← No change!
- Year 2: $10,000 ← No change!
- Year 3: $10,000 ← No change!

**Conclusion:** Surplus is calculated but never accumulated.

---

## 🔧 Recommended Fixes

### Fix #1: Add Surplus Accumulation Logic (CRITICAL)

**Location:** `engine/core.py`, after line 288 (after withdrawal logic)

**Proposed Logic:**
```python
# Calculate net cash flow for the year
total_cash_inflow = emp_p1 + emp_p2 + ss_total + pens_total + current_rental_income
total_cash_outflow = spend_goal + total_mortgage_payment
net_cash_flow = total_cash_inflow - total_cash_outflow

# Add surplus to taxable account (or specify contributions via new params)
if net_cash_flow > 0:
    # Positive cash flow - add to accounts
    # Default: Add to taxable account
    surplus_to_taxable = net_cash_flow - tax_bill  # After-tax surplus
    b_taxable += surplus_to_taxable
```

**Alternative (More Sophisticated):**
Add configuration parameters for contribution allocation:
- `contribution_pretax_p1_pct`: % of surplus to P1's 401k
- `contribution_roth_p1_pct`: % of surplus to P1's Roth
- `contribution_taxable_pct`: % of surplus to taxable account

### Fix #2: Model 401k Contributions

**New Parameters Needed:**
```python
# In schemas/simulation.py
p1_401k_contribution_rate: float = Field(ge=0, le=1, default=0.15)  # 15%
p1_401k_employer_match_rate: float = Field(ge=0, le=0.1, default=0.05)  # 5%
p2_401k_contribution_rate: float = Field(ge=0, le=1, default=0.15)
p2_401k_employer_match_rate: float = Field(ge=0, le=0.1, default=0.05)
p1_401k_is_roth: bool = False  # Traditional vs Roth 401k
p2_401k_is_roth: bool = False
```

**Logic to Add:**
```python
# During employment years
if p1_age < config['p1_employment_until_age'] and emp_p1 > 0:
    p1_contribution = emp_p1 * config.get('p1_401k_contribution_rate', 0.15)
    p1_match = emp_p1 * config.get('p1_401k_employer_match_rate', 0.05)
    
    if config.get('p1_401k_is_roth', False):
        b_roth_p1 += (p1_contribution + p1_match)
    else:
        b_pretax_p1 += (p1_contribution + p1_match)
    
    # Reduce taxable income by pretax contribution (if traditional)
    if not config.get('p1_401k_is_roth', False):
        emp_p1 -= p1_contribution  # Pretax reduces taxable income
```

### Fix #3: Improve Tax Timing

**Option A: Include Tax Withholding in Income Flow**
Treat taxes as paid from current year income, not withdrawn from accounts.

**Option B: Model Quarterly Estimated Payments**
More accurate for self-employed/high-income individuals.

**Option C: Adjust Cash Need Calculation**
```python
# Current year cash needs (before considering income)
spending_need = spend_goal + total_mortgage_payment

# Income available to cover needs
available_income = emp_p1 + emp_p2 + ss_total + pens_total + current_rental_income

# Only need withdrawals if income < spending
if available_income < spending_need + previous_year_taxes:
    cash_need = (spending_need + previous_year_taxes) - available_income
else:
    cash_need = 0  # Income covers everything
    surplus = available_income - (spending_need + previous_year_taxes)
    # Add surplus to accounts
```

### Fix #4: Add Contribution Parameters

Add optional parameters for:
- One-time contributions (inheritance, bonus, etc.)
- Periodic contributions not tied to employment
- Contribution schedules by year

---

## 🎯 Priority Recommendations

### Immediate (Week 1)
1. ✅ Create backup (DONE)
2. 🔴 Fix #1: Add surplus accumulation logic
3. 🔴 Add automated tests for accumulation scenarios

### Short-term (Week 2-3)
4. 🟡 Fix #2: Add 401k contribution modeling
5. 🟡 Fix #3: Improve tax timing logic
6. 🟢 Add better validation/warnings for unrealistic scenarios

### Long-term (Month 2+)
7. Add contribution configuration UI in frontend
8. Add "contribution strategies" similar to withdrawal strategies
9. Model Roth conversion strategies during accumulation years
10. Add scenario comparison (with/without 401k max, etc.)

---

## 📝 Testing Recommendations

### Test Scenarios to Add

1. **Young Professional (Age 25-35)**
   - High income, low savings
   - Should accumulate wealth rapidly
   - Test various 401k contribution rates

2. **Mid-Career (Age 40-55)**
   - Moderate savings, moderate income
   - Should show realistic account growth
   - Test catch-up contributions (age 50+)

3. **Pre-Retirement (Age 55-64)**
   - High savings, high income
   - Should optimize Roth conversions
   - Test transition to retirement

4. **Retirement (Age 65+)**
   - Current scenario (works well)
   - Test RMD calculations
   - Test withdrawal strategies

5. **Edge Cases**
   - Zero savings, high income
   - High savings, zero income
   - One spouse working, one retired
   - Self-employed with variable income

---

## 🔍 Code Quality Observations

### Positive Aspects ✅
- Well-structured layered architecture
- Good separation of concerns (API → Service → Engine)
- Clear withdrawal strategy pattern
- Comprehensive tax calculations
- Good mortgage/real estate modeling

### Areas for Improvement ⚠️
- Missing accumulation phase logic
- No contribution modeling
- Tax timing could be more realistic
- Limited test coverage for young users
- No validation warnings for unrealistic inputs

---

## 📚 Related Files

### Files to Modify
- `engine/core.py` - Add accumulation logic (lines 240-300)
- `schemas/simulation.py` - Add contribution parameters
- `services/simulation_service.py` - Update for new params

### Files to Create
- `engine/contributions.py` - Contribution strategy classes
- `tests/test_accumulation.py` - Tests for working years
- `tests/test_contributions.py` - Tests for 401k/IRA contributions

### Documentation to Update
- `README.md` - Update feature list
- `MASTER_DOCUMENTATION.md` - Add accumulation phase docs
- API docs - Document new parameters

---

## 🚀 Next Steps

1. **Review this analysis** with the development team
2. **Prioritize fixes** based on user impact
3. **Create detailed implementation plan** for Fix #1
4. **Set up automated testing** for accumulation scenarios
5. **Plan frontend updates** to expose new parameters
6. **Consider backwards compatibility** for existing saved scenarios

---

## 💡 Additional Considerations

### User Education
Users may need guidance on:
- When to use accumulation vs decumulation mode
- How 401k contributions affect projections
- Why tax withholding matters for accuracy

### Frontend Implications
The frontend will need:
- Toggle between "accumulation" and "retirement" mode
- 401k contribution input fields
- Visual indicators of contribution vs withdrawal years
- Better warnings when simulation assumptions don't match reality

### Data Migration
If existing users have saved scenarios:
- Need migration path to new parameter structure
- Default values for new parameters
- Version tracking for scenarios

---

**End of Analysis**

*For questions or clarifications, refer to the test files:*
- `test_scenario_analysis.py` - Demonstrates the issues
- `test_backend_parity.py` - Original test suite

*Backup Location:*
- `api_v1_backup/`
- `services_v1_backup/`
- `engine_v1_backup/`
- `main_v1_backup.py`
