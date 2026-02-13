# Implementation Guide: Fix Income Accumulation

## Overview

This guide provides the exact code changes needed to fix the critical income accumulation bug.

---

## Change #1: Fix Surplus Accumulation in Core Engine

**File:** `engine/core.py`  
**Function:** `run_deterministic()`  
**Location:** After line 288 (after withdrawal logic, before tax calculation)

### Current Code Structure

```python
# Line 246-288: Withdrawal logic
cash_need = spend_goal + total_mortgage_payment + previous_year_taxes

# Withdrawal strategy execution...
wd_pretax_p1 = s_res['wd_pretax_p1']
wd_pretax_p2 = s_res['wd_pretax_p2']
# ... etc

total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total + current_rental_income

# Line 282-288: Update balances for withdrawals
b_pretax_p1 -= (rmd_p1 + wd_pretax_p1 + conv_p1)
# ... etc

# Line 291: Tax calculation starts
final_ord_income = (emp_p1 + emp_p2 + ss_total + pens_total + 
                   rmd_total + wd_pretax_p1 + wd_pretax_p2 + roth_conversion + current_rental_income)
```

### Insert This Code (After Line 289, Before Line 291)

```python
        # --- 6a. Handle Income Surplus (Accumulation Phase) ---
        # If income exceeds expenses, add surplus to accounts
        # This fixes the bug where employment income surplus was not being saved
        
        # Calculate total cash available from income sources
        total_cash_income = emp_p1 + emp_p2 + ss_total + pens_total + current_rental_income
        
        # Calculate total cash needed (before considering RMDs and withdrawals)
        total_cash_needed = spend_goal + total_mortgage_payment + previous_year_taxes
        
        # Calculate surplus/deficit
        cash_surplus = total_cash_income - total_cash_needed
        
        if cash_surplus > 0:
            # We have surplus income - need to add it to accounts
            # First, estimate taxes on the surplus to get after-tax amount
            # Note: This is approximate since we calculate exact taxes below
            
            # Estimated tax rate (could be made more sophisticated)
            estimated_marginal_rate = config.get('target_tax_bracket_rate', 0.24)
            estimated_taxes_on_surplus = cash_surplus * estimated_marginal_rate
            after_tax_surplus = cash_surplus - estimated_taxes_on_surplus
            
            # Determine where to allocate the surplus
            # Priority: 401k contributions (during employment), then taxable
            
            # 401k Contributions for P1 (if employed)
            if p1_age < config['p1_employment_until_age'] and emp_p1 > 0:
                # Get contribution rate from config (default 15%)
                p1_contrib_rate = config.get('p1_401k_contribution_rate', 0.15)
                p1_match_rate = config.get('p1_401k_employer_match_rate', 0.05)
                
                # Calculate contributions (capped at annual limit, currently $23,000 for 2024)
                p1_max_contrib = 23000  # IRS limit for 2024
                if p1_age >= 50:
                    p1_max_contrib = 30500  # Catch-up contribution
                
                p1_employee_contrib = min(emp_p1 * p1_contrib_rate, p1_max_contrib)
                p1_employer_match = min(emp_p1 * p1_match_rate, p1_max_contrib * 0.5)
                
                # Determine if Roth or Traditional 401k
                p1_is_roth_401k = config.get('p1_401k_is_roth', False)
                
                if p1_is_roth_401k:
                    b_roth_p1 += (p1_employee_contrib + p1_employer_match)
                else:
                    b_pretax_p1 += (p1_employee_contrib + p1_employer_match)
                
                # Reduce after-tax surplus by the contribution amount
                # (For traditional 401k, this is pre-tax so we save more in taxes)
                if not p1_is_roth_401k:
                    # Traditional 401k reduces taxable income
                    after_tax_surplus -= p1_employee_contrib * (1 - estimated_marginal_rate)
                else:
                    # Roth 401k is post-tax
                    after_tax_surplus -= p1_employee_contrib
                
                after_tax_surplus -= p1_employer_match  # Employer match is free money
            
            # 401k Contributions for P2 (if employed)
            if p2_age < config['p2_employment_until_age'] and emp_p2 > 0:
                p2_contrib_rate = config.get('p2_401k_contribution_rate', 0.15)
                p2_match_rate = config.get('p2_401k_employer_match_rate', 0.05)
                
                p2_max_contrib = 23000
                if p2_age >= 50:
                    p2_max_contrib = 30500
                
                p2_employee_contrib = min(emp_p2 * p2_contrib_rate, p2_max_contrib)
                p2_employer_match = min(emp_p2 * p2_match_rate, p2_max_contrib * 0.5)
                
                p2_is_roth_401k = config.get('p2_401k_is_roth', False)
                
                if p2_is_roth_401k:
                    b_roth_p2 += (p2_employee_contrib + p2_employer_match)
                else:
                    b_pretax_p2 += (p2_employee_contrib + p2_employer_match)
                
                if not p2_is_roth_401k:
                    after_tax_surplus -= p2_employee_contrib * (1 - estimated_marginal_rate)
                else:
                    after_tax_surplus -= p2_employee_contrib
                
                after_tax_surplus -= p2_employer_match
            
            # Add remaining surplus to taxable account
            if after_tax_surplus > 0:
                b_taxable += after_tax_surplus
        
        # --- 6b. Original Tax Calculation (now line ~370) ---
```

### Alternative: Simple Version (If You Want to Start Simple)

If the above is too complex to start with, use this simplified version:

```python
        # --- 6a. Handle Income Surplus (Simple Version) ---
        # Calculate surplus
        total_cash_income = emp_p1 + emp_p2 + ss_total + pens_total + current_rental_income
        total_cash_needed = spend_goal + total_mortgage_payment + previous_year_taxes
        cash_surplus = total_cash_income - total_cash_needed
        
        if cash_surplus > 0:
            # Estimate after-tax surplus
            estimated_tax_rate = config.get('target_tax_bracket_rate', 0.24)
            after_tax_surplus = cash_surplus * (1 - estimated_tax_rate)
            
            # Add all surplus to taxable account for now
            # (Can enhance later to model 401k contributions)
            b_taxable += after_tax_surplus
```

---

## Change #2: Add New Schema Parameters

**File:** `schemas/simulation.py`  
**Location:** After line 49 (after taxable_basis_ratio)

### Add These Parameters

```python
    # 401k Contribution Settings (Optional)
    p1_401k_contribution_rate: Optional[float] = Field(ge=0, le=1, default=0.15)
    p1_401k_employer_match_rate: Optional[float] = Field(ge=0, le=0.1, default=0.05)
    p1_401k_is_roth: Optional[bool] = Field(default=False)
    
    p2_401k_contribution_rate: Optional[float] = Field(ge=0, le=1, default=0.15)
    p2_401k_employer_match_rate: Optional[float] = Field(ge=0, le=0.1, default=0.05)
    p2_401k_is_roth: Optional[bool] = Field(default=False)
```

---

## Change #3: Update Tests

**File:** `tests/test_accumulation.py` (NEW FILE)

### Create This Test File

```python
"""
Tests for accumulation phase (working years with positive cash flow)
"""

import pytest
from schemas.simulation import SimulationParams
from services.simulation_service import run_simulation_service


def test_young_professional_accumulation():
    """Test that surplus income is properly accumulated"""
    
    params = SimulationParams(
        p1_start_age=30,
        p2_start_age=30,
        end_simulation_age=40,  # Just 10 years
        inflation_rate=0.0,  # No inflation for simple math
        annual_spend_goal=50000,
        filing_status="MFJ",
        target_tax_bracket_rate=0.22,
        previous_year_taxes=10000,
        
        # High income
        p1_employment_income=100000,
        p1_employment_until_age=65,
        p2_employment_income=100000,
        p2_employment_until_age=65,
        
        # No retirement income yet
        p1_ss_amount=0,
        p1_ss_start_age=67,
        p2_ss_amount=0,
        p2_ss_start_age=67,
        p1_pension=0,
        p1_pension_start_age=67,
        p2_pension=0,
        p2_pension_start_age=67,
        
        # Small starting balances
        bal_taxable=10000,
        bal_pretax_p1=0,
        bal_pretax_p2=0,
        bal_roth_p1=0,
        bal_roth_p2=0,
        
        # No growth for simple math
        growth_rate_taxable=0.0,
        growth_rate_pretax_p1=0.0,
        growth_rate_pretax_p2=0.0,
        growth_rate_roth_p1=0.0,
        growth_rate_roth_p2=0.0,
        taxable_basis_ratio=1.0,
    )
    
    results = run_simulation_service(params)
    
    assert results['success']
    
    # Get results
    years = results['scenarios']['standard']['results']
    
    # Year 1: Should have surplus
    year1 = years[0]
    assert year1['Total_Income'] == 200000
    assert year1['Spend_Goal'] == 50000
    
    # After 10 years with $150k surplus/year, should have substantial savings
    # Even after taxes (~$40k/year), should save ~$110k/year
    # 10 years * $110k = $1.1M minimum
    year10 = years[9]
    
    # Total liquid net worth should be well over $1M
    total_nw = (year10['Bal_Taxable'] + 
                year10['Bal_PreTax_P1'] + 
                year10['Bal_PreTax_P2'] + 
                year10['Bal_Roth_P1'] + 
                year10['Bal_Roth_P2'])
    
    assert total_nw > 1000000, f"Expected >$1M in savings, got ${total_nw:,.0f}"
    
    # Taxable account should have grown significantly
    assert year10['Bal_Taxable'] > 500000, f"Expected >$500k in taxable, got ${year10['Bal_Taxable']:,.0f}"


def test_401k_contributions():
    """Test that 401k contributions are properly modeled"""
    
    params = SimulationParams(
        p1_start_age=30,
        p2_start_age=30,
        end_simulation_age=35,  # 5 years
        inflation_rate=0.0,
        annual_spend_goal=50000,
        filing_status="MFJ",
        target_tax_bracket_rate=0.22,
        previous_year_taxes=10000,
        
        p1_employment_income=100000,
        p1_employment_until_age=65,
        p2_employment_income=0,  # Only P1 working
        p2_employment_until_age=30,  # P2 not working
        
        # 401k settings
        p1_401k_contribution_rate=0.15,  # 15% contribution
        p1_401k_employer_match_rate=0.05,  # 5% match
        p1_401k_is_roth=False,  # Traditional 401k
        
        p1_ss_amount=0,
        p1_ss_start_age=67,
        p2_ss_amount=0,
        p2_ss_start_age=67,
        p1_pension=0,
        p1_pension_start_age=67,
        p2_pension=0,
        p2_pension_start_age=67,
        
        bal_taxable=10000,
        bal_pretax_p1=0,
        bal_pretax_p2=0,
        bal_roth_p1=0,
        bal_roth_p2=0,
        
        growth_rate_taxable=0.0,
        growth_rate_pretax_p1=0.0,
        growth_rate_pretax_p2=0.0,
        growth_rate_roth_p1=0.0,
        growth_rate_roth_p2=0.0,
        taxable_basis_ratio=1.0,
    )
    
    results = run_simulation_service(params)
    assert results['success']
    
    years = results['scenarios']['standard']['results']
    
    # After 5 years:
    # Employee contrib: $100k * 0.15 = $15k/year * 5 = $75k
    # Employer match: $100k * 0.05 = $5k/year * 5 = $25k
    # Total: $100k in pretax account
    
    year5 = years[4]
    
    assert year5['Bal_PreTax_P1'] >= 90000, \
        f"Expected ~$100k in 401k, got ${year5['Bal_PreTax_P1']:,.0f}"


if __name__ == "__main__":
    test_young_professional_accumulation()
    test_401k_contributions()
    print("✓ All accumulation tests passed!")
```

---

## Change #4: Update Documentation

**File:** `README.md`

Add this section:

```markdown
## Accumulation Phase Support

The retirement planner now supports both accumulation (working years) and decumulation (retirement years):

### Working Years
- Automatically accumulates surplus income into accounts
- Models 401k contributions (employee + employer match)
- Supports both Traditional and Roth 401k
- Respects IRS contribution limits

### Configuration
```python
{
  "p1_401k_contribution_rate": 0.15,  # 15% of salary
  "p1_401k_employer_match_rate": 0.05,  # 5% match
  "p1_401k_is_roth": false  # Traditional vs Roth
}
```

### Retirement Years
- RMD calculations
- Withdrawal strategies (Standard vs Taxable-First)
- Roth conversion optimization
```

---

## Testing Checklist

After implementing the changes:

- [ ] Run `python test_scenario_analysis.py` - should show surplus being saved
- [ ] Run `python tests/test_accumulation.py` - should pass
- [ ] Run existing tests - should still pass
- [ ] Test via API with frontend
- [ ] Test edge cases:
  - [ ] Zero income (retirees only) - should work as before
  - [ ] High income, low spending - should accumulate
  - [ ] Income exactly equals spending - should maintain balance
  - [ ] 401k contribution exceeds IRS limits - should cap at limit

---

## Rollback Plan

If issues occur after deployment:

1. The original code is backed up in:
   - `engine_v1_backup/core.py`
   - `schemas_v1_backup/simulation.py`

2. To rollback:
```bash
cp engine_v1_backup/core.py engine/core.py
cp schemas_v1_backup/simulation.py schemas/simulation.py
# Restart server
```

3. Or use git to revert to previous commit

---

## Questions?

- See `CALCULATION_ISSUES_ANALYSIS.md` for detailed analysis
- See `ISSUES_QUICK_REFERENCE.md` for quick overview
- See `test_scenario_analysis.py` for examples of the bug

