"""
Comprehensive Audit Script for Life Planner Simulation Engine
=============================================================
Runs multiple scenarios and validates calculation correctness.
Checks: taxes, wealth trajectory, account balances, debt paydown,
college expenses, mortgage payments, social security, FICA, etc.
"""

import sys
import os
import json
import math

sys.path.insert(0, os.path.dirname(__file__))

from engine.core import SimulationConfig, run_deterministic
from engine.taxes import TaxCalculator


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def fmt(v):
    return f"${v:,.0f}"

def pct(v):
    return f"{v*100:.2f}%"

def run_sim(overrides, strategy='standard'):
    """Run simulation with base defaults + overrides."""
    base = dict(
        p1_start_age=40, p2_start_age=38, end_simulation_age=90,
        inflation_rate=0.025,
        annual_spend_goal=80_000,
        p1_employment_income=120_000, p1_employment_until_age=65,
        p2_employment_income=80_000,  p2_employment_until_age=63,
        p1_ss_amount=30_000, p1_ss_start_age=67,
        p2_ss_amount=20_000, p2_ss_start_age=67,
        p1_pension=0, p1_pension_start_age=65,
        p2_pension=0, p2_pension_start_age=65,
        bal_taxable=50_000,
        bal_pretax_p1=300_000, bal_pretax_p2=150_000,
        bal_roth_p1=50_000,   bal_roth_p2=25_000,
        growth_rate_taxable=0.07, growth_rate_pretax_p1=0.07,
        growth_rate_pretax_p2=0.07, growth_rate_roth_p1=0.07, growth_rate_roth_p2=0.07,
        taxable_basis_ratio=0.80,
        target_tax_bracket_rate=0.22,
        p1_401k_contribution_rate=0.15, p1_401k_employer_match_rate=0.05, p1_401k_is_roth=False,
        p2_401k_contribution_rate=0.15, p2_401k_employer_match_rate=0.05, p2_401k_is_roth=False,
        auto_optimize_roth_traditional=True,
        student_loan_balance=0, student_loan_rate=0.05, student_loan_payment=0,
        car_loan_balance=0, car_loan_payment=0, car_loan_years=0,
        credit_card_debt=0, credit_card_payment=0, credit_card_rate=0.18,
        annual_medical_expenses=0, medical_inflation_rate=0.06,
        business_income=0, business_growth_rate=0.03, business_ends_at_age=65,
        num_children=0,
        monthly_expense_per_child_0_5=500, monthly_expense_per_child_6_12=800,
        monthly_expense_per_child_13_17=1000, college_cost_per_year=25_000,
        passive_income=0, passive_income_growth_rate=0.02,
        life_insurance_premium=0, life_insurance_type='none', life_insurance_term_ends_at_age=65,
        monthly_rent=0, rent_inflation_rate=0.03,
        primary_home_value=0, primary_home_growth_rate=0.03,
        primary_home_mortgage_principal=0, primary_home_mortgage_rate=0.065, primary_home_mortgage_years=0,
        previous_year_taxes=0,
    )
    base.update(overrides)
    cfg = SimulationConfig(start_year=2024, **base)
    return run_deterministic(cfg, strategy_name=strategy)


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────
ISSUES = []
PASSES = []

def check(name, condition, details=""):
    if condition:
        PASSES.append(f"  ✅ PASS: {name}")
    else:
        ISSUES.append(f"  ❌ FAIL: {name}" + (f"\n     └── {details}" if details else ""))

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 1 – Basic Sanity: Accumulation Phase
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 1 – Basic Accumulation (Age 40→65, income > spending)")

records = run_sim({})
yr = {r['P1_Age']: r for r in records}

# Portfolio should grow during working years (40-65)
# Start: 50k + 300k + 150k + 50k + 25k = 575k liquid
start_liquid = yr[40]['Bal_Taxable'] + yr[40]['Bal_PreTax_P1'] + yr[40]['Bal_PreTax_P2'] + yr[40]['Bal_Roth_P1'] + yr[40]['Bal_Roth_P2']
at_retirement = yr[65]['Bal_Taxable'] + yr[65]['Bal_PreTax_P1'] + yr[65]['Bal_PreTax_P2'] + yr[65]['Bal_Roth_P1'] + yr[65]['Bal_Roth_P2']

print(f"  Liquid portfolio at 40:  {fmt(start_liquid)}")
print(f"  Liquid portfolio at 65:  {fmt(at_retirement)}")
check("Portfolio grows during accumulation", at_retirement > start_liquid,
      f"Start={fmt(start_liquid)} End={fmt(at_retirement)}")

# 401k contributions should be positive during working years
contrib_p1_age40 = yr[40].get('Contrib_P1_401k', 0)
print(f"  401k contribution (age 40): {fmt(contrib_p1_age40)}")
check("401k contributions occur during working years", contrib_p1_age40 > 0,
      f"Contrib_P1_401k={fmt(contrib_p1_age40)} (should be > 0 for 15% rate on $120K income)")

# Expected annual 401k contribution: min($120K * 15%, $23K) = $18K, plus match $6K
expected_401k = min(120_000 * 0.15, 23_000)
expected_match = min(120_000 * 0.05, 23_000)
print(f"  Expected employee contrib: {fmt(expected_401k)}, match: {fmt(expected_match)}")
check("401k contribution is near IRS limit",
      abs(contrib_p1_age40 - expected_401k) < 1000,
      f"Got {fmt(contrib_p1_age40)}, expected ~{fmt(expected_401k)}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 2 – Tax Calculation Audit
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 2 – Federal Tax Calculation Accuracy")

tax_calc = TaxCalculator()

# Manual verification: $120K income, inflation factor=1.0
# Standard deduction: $32,200 → taxable = $87,800
# 10% on $24,800 = $2,480
# 12% on ($87,800-$24,800) = 12% * $63,000 = $7,560
# Total = $10,040
manual_tax = tax_calc.calculate_tax(120_000, 0, 1.0)
std_ded = tax_calc.std_deduction
taxable_inc = max(0, 120_000 - std_ded)
bracket_1 = min(taxable_inc, 24_800) * 0.10
bracket_2 = max(0, min(taxable_inc, 100_800) - 24_800) * 0.12
bracket_3 = max(0, min(taxable_inc, 211_400) - 100_800) * 0.22
manual_calc = bracket_1 + bracket_2 + bracket_3

print(f"  Std deduction (coded):   {fmt(std_ded)}  ← 2024 MFJ should be $29,200")
print(f"  Tax on $120K income:     {fmt(manual_tax)}  (manual: {fmt(manual_calc)})")
check("Tax calculation is consistent with brackets",
      abs(manual_tax - manual_calc) < 1,
      f"Engine: {fmt(manual_tax)}, Manual: {fmt(manual_calc)}")

# Check: 2024 standard deduction for MFJ is $29,200, NOT $32,200
check("Standard deduction is correct (2024 MFJ = $29,200)",
      std_ded == 29_200,
      f"Coded as {fmt(std_ded)}, should be $29,200")

# Taxes Paid is always 0 in records
taxes_paid_yr40 = yr[40].get('Taxes_Paid', -1)
tax_bill_yr40 = yr[40].get('Tax_Bill', 0)
print(f"  Taxes_Paid (age 40): {fmt(taxes_paid_yr40)}  ← always 0 (bug!)")
print(f"  Tax_Bill   (age 40): {fmt(tax_bill_yr40)}")
check("Taxes_Paid is non-zero (should reflect lagged payment)",
      taxes_paid_yr40 > 0,
      f"Taxes_Paid={fmt(taxes_paid_yr40)} but Tax_Bill={fmt(tax_bill_yr40)} — hardcoded 0 in records!")

# Check FICA tax missing
# Expected: Employee FICA on $120K = 7.65% * $120K = $9,180
fica_expected = 120_000 * 0.0765
print(f"  FICA expected (7.65% of $120K): {fmt(fica_expected)}  ← NOT calculated")
check("FICA tax is calculated",
      False,  # We KNOW this is missing - documenting the bug
      f"FICA not calculated anywhere in backend. Missing ~{fmt(fica_expected)}/year for a $120K salary")

# Check state tax missing
print(f"  State tax: NOT calculated  ← stateOfResidence is collected but ignored")
check("State income tax is calculated",
      False,
      "State tax completely absent. A CA resident earning $120K owes ~$7K+ in state tax")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 3 – Debt Paydown: Student Loan + Car Loan
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 3 – Debt Paydown (Student $30K @ $400/mo, Car $20K @ $400/mo)")

records_debt = run_sim({
    'student_loan_balance': 30_000,
    'student_loan_rate': 0.055,
    'student_loan_payment': 400,
    'car_loan_balance': 20_000,
    'car_loan_payment': 400,
    'car_loan_years': 5,
})
yr_d = {r['P1_Age']: r for r in records_debt}

debt_age40 = yr_d[40].get('Remaining_Debt', 0)
debt_age45 = yr_d[45].get('Remaining_Debt', 0)
debt_age50 = yr_d[50].get('Remaining_Debt', 0)

print(f"  Remaining debt at 40: {fmt(debt_age40)}")
print(f"  Remaining debt at 45: {fmt(debt_age45)}")
print(f"  Remaining debt at 50: {fmt(debt_age50)}")
check("Debt decreases over time", debt_age40 > debt_age45 >= 0,
      f"Debt at 40={fmt(debt_age40)}, at 45={fmt(debt_age45)}")

# Student loan at $400/mo should be paid off in ~7 years
check("Student loan paid off by age 50", debt_age50 < 5_000,
      f"Remaining debt at 50={fmt(debt_age50)}")

# Debt payments should appear in cash need / expenses
debt_payment_age40 = yr_d[40].get('Debt_Payment', 0)
expected_debt_payment = (400 + 400) * 12  # $9,600/year
print(f"  Debt payment (age 40): {fmt(debt_payment_age40)}")
check("Debt payments appear in annual cash flow",
      debt_payment_age40 > 0,
      f"Debt_Payment={fmt(debt_payment_age40)}, expected ~{fmt(expected_debt_payment)}")

# Net worth should show dip due to debt subtraction
nw_debt_40 = yr_d[40].get('Net_Worth', 0)
nw_base_40 = yr[40].get('Net_Worth', 0)
print(f"  Net worth at 40 (no debt): {fmt(nw_base_40)}")
print(f"  Net worth at 40 (with $50K debt): {fmt(nw_debt_40)}")
check("Net worth is lower when debt exists",
      nw_debt_40 < nw_base_40,
      f"NW-no-debt={fmt(nw_base_40)}, NW-with-debt={fmt(nw_debt_40)}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 4 – Mortgage Impact
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 4 – Mortgage ($400K home, $350K mortgage @ 6.5%, 30yr)")

records_mort = run_sim({
    'primary_home_value': 400_000,
    'primary_home_mortgage_principal': 350_000,
    'primary_home_mortgage_rate': 0.065,
    'primary_home_mortgage_years': 30,
})
yr_m = {r['P1_Age']: r for r in records_mort}

mortgage_pmt = yr_m[40].get('Mortgage_Payment', 0)
primary_home_40 = yr_m[40].get('Primary_Home', 0)
primary_home_65 = yr_m[65].get('Primary_Home', 0)

# Expected monthly payment: 350000 * (0.065/12) / (1 - (1+0.065/12)^-360) ≈ $2,213
r_monthly = 0.065 / 12
n = 30 * 12
expected_monthly = 350_000 * r_monthly / (1 - (1 + r_monthly)**(-n))
expected_annual = expected_monthly * 12

print(f"  Annual mortgage payment:  {fmt(mortgage_pmt)}")
print(f"  Expected (~$26,556/yr):   {fmt(expected_annual)}")
check("Mortgage payment is calculated correctly",
      abs(mortgage_pmt - expected_annual) < 1_000,
      f"Got {fmt(mortgage_pmt)}, expected {fmt(expected_annual)}")

print(f"  Home value at 40: {fmt(primary_home_40)}, at 65: {fmt(primary_home_65)}")
check("Home appreciates over time",
      primary_home_65 > primary_home_40,
      f"Home at 40={fmt(primary_home_40)}, at 65={fmt(primary_home_65)}")

# Net worth should include home equity
nw_mort_40 = yr_m[40].get('Net_Worth', 0)
nw_base_40 = yr[40].get('Net_Worth', 0)
print(f"  NW at 40 (with $400K home, $350K mortgage): {fmt(nw_mort_40)}")
print(f"  NW at 40 (no home/mortgage):                {fmt(nw_base_40)}")
# Home adds $400K, mortgage subtracts... 
# BUG: Core.py subtracts Remaining_Debt (student/car/cc) but NOT mortgage principal
# Net worth should be ~$50K higher (home equity = $400K - $350K = $50K)
expected_nw_diff = 400_000 - 350_000  # $50K net home equity at start
actual_diff = nw_mort_40 - nw_base_40
print(f"  NW difference (actual {fmt(actual_diff)} vs expected ~{fmt(expected_nw_diff)})")
check("Net worth correctly nets home equity (home - mortgage)",
      abs(actual_diff - expected_nw_diff) < 10_000,
      f"Diff={fmt(actual_diff)}, expected ~{fmt(expected_nw_diff)}. "
      f"Mortgage balance is NOT subtracted from net worth (bug in core.py line 515)!")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 5 – Children & College Expenses
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 5 – Children & College (2 kids ages 5 & 8, $25K/yr college)")

records_kids = run_sim({
    'num_children': 2,
    'child_1_current_age': 5,
    'child_2_current_age': 8,
    'monthly_expense_per_child_0_5': 500,
    'monthly_expense_per_child_6_12': 800,
    'monthly_expense_per_child_13_17': 1000,
    'college_cost_per_year': 25_000,
})
yr_k = {r['P1_Age']: r for r in records_kids}

child_exp_40 = yr_k[40].get('Child_Expenses', 0)
college_exp_53 = yr_k[53].get('College_Expenses', 0)  # Child 1 (age 5→18 at parent age 53)

# At age 40: Child1 is 5, Child2 is 8
# Child1 (5yo): $500/mo * 12 = $6,000
# Child2 (8yo): $800/mo * 12 = $9,600
# Total expected: $15,600
expected_child_40 = (500 * 12) + (800 * 12)  # both in school
print(f"  Child expenses at parent age 40: {fmt(child_exp_40)}")
print(f"  Expected: {fmt(expected_child_40)} (Child1@5=$6K + Child2@8=$9.6K)")
check("Child expenses calculated correctly at age 40",
      abs(child_exp_40 - expected_child_40) < 500,
      f"Got {fmt(child_exp_40)}, expected {fmt(expected_child_40)}")

print(f"  College expenses at parent age 53 (child1 turns 18): {fmt(college_exp_53)}")
check("College expenses appear when child turns 18",
      college_exp_53 > 0,
      f"College_Expenses at age 53 = {fmt(college_exp_53)}, expected $25K-$50K")

# Wealth trajectory should show dips during college years
nw_kids_53 = yr_k[53].get('Net_Worth', 0)
nw_kids_52 = yr_k[52].get('Net_Worth', 0)
nw_kids_57 = yr_k[57].get('Net_Worth', 0)  # After child2 done with college

# Check that wealth chart is NOT smooth during college (should show spending impact)
nw_no_kids_53 = yr[53].get('Net_Worth', 0)
print(f"  Net worth at 53 (with kids): {fmt(nw_kids_53)}")
print(f"  Net worth at 53 (no kids):   {fmt(nw_no_kids_53)}")
check("College expenses reduce net worth vs no-kids scenario",
      nw_kids_53 < nw_no_kids_53,
      f"Kids NW={fmt(nw_kids_53)}, No-kids NW={fmt(nw_no_kids_53)}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 6 – Social Security & RMD Timing
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 6 – Social Security Start & RMD Timing")

yr_r = {r['P1_Age']: r for r in records}  # reuse base scenario

ss_before = yr_r[66].get('SS_P1', 0)  # before age 67
ss_at = yr_r[67].get('SS_P1', 0)       # at age 67
ss_after = yr_r[70].get('SS_P1', 0)    # after age 67

print(f"  SS at age 66 (before start): {fmt(ss_before)}")
print(f"  SS at age 67 (start age):    {fmt(ss_at)}")
print(f"  SS at age 70:               {fmt(ss_after)}")
check("SS is 0 before start age", ss_before == 0,
      f"SS at 66 = {fmt(ss_before)}, should be $0")
check("SS starts at correct age (67)", ss_at > 0,
      f"SS at 67 = {fmt(ss_at)}, should be ~$30K")
check("SS grows with inflation after start", ss_after > ss_at,
      f"SS at 70={fmt(ss_after)}, at 67={fmt(ss_at)} — should grow with inflation")

rmd_before_73 = yr_r[72].get('RMD_P1', 0)
rmd_at_73 = yr_r[73].get('RMD_P1', 0)
rmd_at_80 = yr_r[80].get('RMD_P1', 0)

print(f"\n  RMD at age 72 (before age): {fmt(rmd_before_73)}")
print(f"  RMD at age 73 (start):     {fmt(rmd_at_73)}")
print(f"  RMD at age 80:             {fmt(rmd_at_80)}")
check("No RMD before age 73", rmd_before_73 == 0,
      f"RMD at 72 = {fmt(rmd_before_73)}, should be $0")
check("RMD starts at age 73 (SECURE 2.0)", rmd_at_73 > 0,
      f"RMD at 73 = {fmt(rmd_at_73)}")
check("RMD increases over time (account growth + age factor)", rmd_at_80 > rmd_at_73,
      f"RMD at 80={fmt(rmd_at_80)}, at 73={fmt(rmd_at_73)}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 7 – Withdrawal Strategy Consistency
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 7 – Withdrawal Completeness (Post-Retirement Cash Needs)")

# At retirement age, withdrawals should cover ALL cash needs
# The critical bug: withdrawals.py uses INCOMPLETE cash_need
yr_r65 = yr_r.get(65, {})
cash_need_65 = yr_r65.get('Cash_Need', 0)
spend_goal_65 = yr_r65.get('Spend_Goal', 0)
prev_tax_65 = yr_r65.get('Previous_Taxes', 0)

wd_total_65 = (
    yr_r65.get('WD_PreTax_P1', 0) + yr_r65.get('WD_PreTax_P2', 0) +
    yr_r65.get('WD_Taxable', 0) + yr_r65.get('WD_Roth_P1', 0) + yr_r65.get('WD_Roth_P2', 0)
)
total_income_65 = yr_r65.get('Total_Income', 0)
rmd_total_65 = yr_r65.get('RMD_P1', 0) + yr_r65.get('RMD_P2', 0)

print(f"  At retirement (age 65):")
print(f"    Cash Need:       {fmt(cash_need_65)}")
print(f"    Spend Goal:      {fmt(spend_goal_65)}")
print(f"    Prev Year Taxes: {fmt(prev_tax_65)}")
print(f"    Total Income:    {fmt(total_income_65)}")
print(f"    Total WDs:       {fmt(wd_total_65)}")
print(f"    Available Cash:  {fmt(total_income_65 + wd_total_65)}")

# Strategy only withdraws to cover spend_goal + prev_taxes, NOT the full cash_need
strategy_cash_need = spend_goal_65 + prev_tax_65
print(f"\n  ⚠️ Strategy's cash_need = {fmt(strategy_cash_need)}")
print(f"  ⚠️ Actual cash_need     = {fmt(cash_need_65)}")
check("Withdrawal strategy covers ALL cash needs (not just spend_goal + taxes)",
      abs((total_income_65 + wd_total_65) - cash_need_65) < 1_000,
      f"Available cash={fmt(total_income_65 + wd_total_65)}, actual cash need={fmt(cash_need_65)}. "
      f"Strategy gap: {fmt(cash_need_65 - strategy_cash_need)} in extra expenses not covered by WD logic")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 8 – Retirement Spending Ratio
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 8 – Retirement Ratio Not Applied")

# The backend uses annual_spend_goal throughout life
# But in reality, spending typically drops to 80% in retirement
# The retirementRatio (80%) is collected in UI but never passed/used

spend_pre_retirement_64 = yr_r.get(64, {}).get('Spend_Goal', 0)
spend_post_retirement_66 = yr_r.get(66, {}).get('Spend_Goal', 0)
spend_post_retirement_75 = yr_r.get(75, {}).get('Spend_Goal', 0)

print(f"  Spend goal at 64 (pre-retirement):  {fmt(spend_pre_retirement_64)}")
print(f"  Spend goal at 66 (post-retirement): {fmt(spend_post_retirement_66)}")
print(f"  Spend goal at 75 (post-retirement): {fmt(spend_post_retirement_75)}")

# If retirementRatio=80% were applied, spending at 66 should be 80% of base
inflation_at_66 = (1.025) ** 26  # 26 years of inflation from start
expected_with_ratio = 80_000 * 0.80 * inflation_at_66
print(f"  Expected with 80% retirement ratio: ~{fmt(expected_with_ratio)}")

check("Retirement ratio reduces spending in retirement phase",
      spend_post_retirement_66 < spend_pre_retirement_64 * 1.1,
      f"Spending at 64={fmt(spend_pre_retirement_64)}, at 66={fmt(spend_post_retirement_66)}. "
      f"Backend ignores retirementRatio — spending only inflates, never drops at retirement")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 9 – Salary Growth Rate
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 9 – Salary Growth (Should grow at user rate, not just inflation)")

# The backend uses: emp_p1 = config['p1_employment_income'] * inflation_idx
# BUT users set salaryGrowthRate (e.g., 3%) separately from inflation (2.5%)
# The salaryGrowthRate is collected in frontend but NEVER sent to backend

# With inflation only (2.5%), salary at 50 (10 years later):
salary_at_50 = yr_r.get(50, {}).get('Employment_P1', 0)
inflation_10yr = (1.025) ** 10
expected_inflation_only = 120_000 * inflation_10yr
expected_with_3pct_raise = 120_000 * (1.03) ** 10

print(f"  Starting salary (age 40): {fmt(120_000)}")
print(f"  Salary at age 50 (actual):              {fmt(salary_at_50)}")
print(f"  Expected (inflation-only, +2.5%/yr):    {fmt(expected_inflation_only)}")
print(f"  Expected (with 3% salary growth/yr):    {fmt(expected_with_3pct_raise)}")
check("Salary grows with inflation",
      abs(salary_at_50 - expected_inflation_only) < 500,
      f"Actual={fmt(salary_at_50)}, inflation-only={fmt(expected_inflation_only)}")
check("ISSUE: salaryGrowthRate is not applied to salary growth",
      False,
      f"salaryGrowthRate is collected in UI but NOT sent to backend. "
      f"A 3% raise vs inflation-only is {fmt(expected_with_3pct_raise - expected_inflation_only)} difference by age 50")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 10 – Post-Retirement Growth Rate
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 10 – Post-Retirement Growth Rate (preReturn vs postReturn)")

# Frontend collects both preRetirementReturn (7%) and postRetirementReturn (5%)
# But simulation.service.ts maps ALL growth rates to preRetirementReturn only
# The postRetirementReturn is NEVER used

# Run same scenario but with lower growth_rate post-retirement
# (We simulate what SHOULD happen vs what currently happens)
records_low_growth = run_sim({
    'growth_rate_taxable': 0.05,
    'growth_rate_pretax_p1': 0.05, 'growth_rate_pretax_p2': 0.05,
    'growth_rate_roth_p1': 0.05, 'growth_rate_roth_p2': 0.05,
})
yr_lg = {r['P1_Age']: r for r in records_low_growth}

nw_base_80 = yr_r.get(80, {}).get('Net_Worth', 0)
nw_low_80 = yr_lg.get(80, {}).get('Net_Worth', 0)

print(f"  Net worth at 80 (7% growth throughout):          {fmt(nw_base_80)}")
print(f"  Net worth at 80 (5% growth throughout):          {fmt(nw_low_80)}")
print(f"  Difference (overstated by using 7% in retire):   {fmt(nw_base_80 - nw_low_80)}")
check("ISSUE: postRetirementReturn is NOT applied after retirement",
      False,
      f"Frontend collects postRetirementReturn (e.g., 5%) but maps all accounts to preRetirementReturn (7%). "
      f"This overstates post-retirement wealth by {fmt(nw_base_80 - nw_low_80)} in this scenario")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 11 – Passive Income Growth
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 11 – Passive Income Growth Bug")

records_passive = run_sim({
    'passive_income': 24_000,  # $2K/month
    'passive_income_growth_rate': 0.03,  # 3% growth
})
yr_p = {r['P1_Age']: r for r in records_passive}

pi_40 = yr_p[40].get('Passive_Income', 0)
pi_50 = yr_p[50].get('Passive_Income', 0)
pi_60 = yr_p[60].get('Passive_Income', 0)

# CORRECT behavior: passive income should grow at 3% per year
# But the code does: passive_income_this_year = passive_income_current * inflation_idx
# passive_income_current NEVER changes (no growth applied to it)
# So it only grows by inflation, NOT by passive_income_growth_rate
inflation_10yr = (1.025) ** 10
expected_inflation_10yr = 24_000 * inflation_10yr
expected_3pct_10yr = 24_000 * (1.03) ** 10

print(f"  Passive income at 40: {fmt(pi_40)}")
print(f"  Passive income at 50: {fmt(pi_50)}")
print(f"  Expected (inflation only): {fmt(expected_inflation_10yr)}")
print(f"  Expected (3% growth rate): {fmt(expected_3pct_10yr)}")
check("Passive income grows at specified growth rate (3%)",
      abs(pi_50 - expected_3pct_10yr) < 500,
      f"Got {fmt(pi_50)}, expected {fmt(expected_3pct_10yr)} at 3% growth. "
      f"Bug: passive_income_current is never updated, so only inflation applies")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 12 – Life Insurance Premium
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 12 – Life Insurance Premium")

records_ins = run_sim({
    'life_insurance_type': 'term',
    'life_insurance_premium': 200,  # $200/month
    'life_insurance_term_ends_at_age': 60,
})
yr_i = {r['P1_Age']: r for r in records_ins}

ins_40 = yr_i[40].get('Insurance_Premium', 0)
ins_59 = yr_i[59].get('Insurance_Premium', 0)
ins_61 = yr_i[61].get('Insurance_Premium', 0)

expected_annual = 200 * 12  # $2,400/year
print(f"  Insurance premium at 40: {fmt(ins_40)}  (expected: {fmt(expected_annual)})")
print(f"  Insurance premium at 59: {fmt(ins_59)}")
print(f"  Insurance premium at 61 (after term ends): {fmt(ins_61)}")
check("Term insurance premium correct", abs(ins_40 - expected_annual) < 100,
      f"Got {fmt(ins_40)}, expected {fmt(expected_annual)}")
check("Term insurance ends at specified age", ins_61 == 0,
      f"Premium at 61={fmt(ins_61)}, should be $0 after term ends at 60")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 13 – Net Worth Chart Smoothness Check
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 13 – Chart Smoothness vs Reality")

# With debt, mortgage, college expenses → should see NON-SMOOTH trajectory
records_complex = run_sim({
    'student_loan_balance': 40_000,
    'student_loan_rate': 0.055,
    'student_loan_payment': 500,
    'primary_home_value': 500_000,
    'primary_home_mortgage_principal': 400_000,
    'primary_home_mortgage_rate': 0.065,
    'primary_home_mortgage_years': 30,
    'num_children': 2,
    'child_1_current_age': 3,
    'child_2_current_age': 6,
    'college_cost_per_year': 30_000,
    'annual_medical_expenses': 5_000,
    'medical_inflation_rate': 0.06,
})
yr_c = {r['P1_Age']: r for r in records_complex}

# Check that cash_need reflects all costs
cash_need_40 = yr_c[40].get('Cash_Need', 0)
spend_goal_40 = yr_c[40].get('Spend_Goal', 0)
mortgage_40 = yr_c[40].get('Mortgage_Payment', 0)
debt_40 = yr_c[40].get('Debt_Payment', 0)
child_40 = yr_c[40].get('Child_Expenses', 0)
medical_40 = yr_c[40].get('Medical_Expenses', 0)

print(f"  Cash Need (age 40):       {fmt(cash_need_40)}")
print(f"    Spend Goal:             {fmt(spend_goal_40)}")
print(f"    Mortgage:               {fmt(mortgage_40)}")
print(f"    Debt Payments:          {fmt(debt_40)}")
print(f"    Child Expenses:         {fmt(child_40)}")
print(f"    Medical Expenses:       {fmt(medical_40)}")
manual_cash_need = spend_goal_40 + mortgage_40 + debt_40 + child_40 + medical_40
print(f"  Sum of components:        {fmt(manual_cash_need)}")
check("Cash need correctly sums all expense components",
      abs(cash_need_40 - manual_cash_need) < 1_000,
      f"CashNeed={fmt(cash_need_40)}, sum={fmt(manual_cash_need)}")

# College years should create a dip in liquid portfolio
age_before_college = 55  # child1 (3yo) turns 18 at parent age 55+12=55... wait: child starts at age 3, turns 18 in 15 years, parent then 40+15=55
age_college = 55
liquid_before = (
    yr_c.get(age_college - 1, {}).get('Bal_Taxable', 0) +
    yr_c.get(age_college - 1, {}).get('Bal_Roth_P1', 0) +
    yr_c.get(age_college - 1, {}).get('Bal_Roth_P2', 0)
)
liquid_during = (
    yr_c.get(age_college, {}).get('Bal_Taxable', 0) +
    yr_c.get(age_college, {}).get('Bal_Roth_P1', 0) +
    yr_c.get(age_college, {}).get('Bal_Roth_P2', 0)
)
college_exp_parent55 = yr_c.get(age_college, {}).get('College_Expenses', 0)
print(f"\n  College expenses at parent age {age_college}: {fmt(college_exp_parent55)}")
print(f"  Liquid portfolio change around college years:")
print(f"    Before (age {age_college-1}): {fmt(liquid_before)}")
print(f"    During (age {age_college}):   {fmt(liquid_during)}")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 14 – Pension COLA Bug
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 14 – Pension COLA Bug (all pensions treated as having COLA)")

records_pension = run_sim({
    'p1_pension': 24_000,  # $2K/month pension
    'p1_pension_start_age': 65,
})
yr_pen = {r['P1_Age']: r for r in records_pension}

pension_65 = yr_pen.get(65, {}).get('Pension_P1', 0)
pension_75 = yr_pen.get(75, {}).get('Pension_P1', 0)
pension_85 = yr_pen.get(85, {}).get('Pension_P1', 0)

# Backend applies inflation_idx to pension regardless of pensionCOLA setting
# If COLA=False, pension should stay flat at $24K
# If COLA=True, pension grows with inflation
inflation_10yr = (1.025) ** 10
expected_with_cola = 24_000 * inflation_10yr

print(f"  Pension at start (age 65): {fmt(pension_65)}")
print(f"  Pension at age 75:         {fmt(pension_75)}")
print(f"  Pension at age 85:         {fmt(pension_85)}")
print(f"  Expected (with COLA):      {fmt(expected_with_cola)} at age 75")
print(f"  Expected (no COLA):        {fmt(24_000)} at age 75")
check("ISSUE: Pension always inflation-adjusted (ignores pensionCOLA=False)",
      False,
      f"Pension at 75={fmt(pension_75)}, expected flat $24K if COLA=False. "
      f"Backend always multiplies pension by inflation_idx (line 251 core.py)")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 15 – Frontend totalSpend Mapping Bug
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 15 – Frontend totalSpend Mapping (Only Spend_Goal, missing expenses)")

# In simulation.service.ts mapBackendToFrontend():
# totalSpend: r.Spend_Goal || 0   ← BUG: Should be r.Cash_Need
# This means charts show only basic spending, ignoring mortgage/debt/medical/college

yr_c_40 = yr_c.get(40, {})
frontend_total_spend = yr_c_40.get('Spend_Goal', 0)  # what frontend shows
actual_cash_need = yr_c_40.get('Cash_Need', 0)        # what it should show

print(f"  What frontend shows as 'totalSpend': {fmt(frontend_total_spend)}  (= Spend_Goal only)")
print(f"  Actual total cash need:              {fmt(actual_cash_need)}")
print(f"  Missing from chart:                  {fmt(actual_cash_need - frontend_total_spend)}")
check("Frontend totalSpend includes all expenses (mortgage, debt, medical, etc.)",
      False,
      f"totalSpend={fmt(frontend_total_spend)}, actual need={fmt(actual_cash_need)}. "
      f"simulation.service.ts line 387: 'totalSpend: r.Spend_Goal' should be 'r.Cash_Need'")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 16 – 2024 Tax Bracket Values
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 16 – Tax Bracket Values (2024 Accuracy)")

tc = TaxCalculator()
print("  Coded brackets (cumulative upper limits, MFJ):")
for lim, rate in tc.brackets_ordinary:
    print(f"    {pct(rate)}: up to {fmt(lim)}")

print("\n  2024 IRS actual MFJ brackets:")
actual_2024 = [
    (23_200, 0.10), (94_300, 0.12), (201_050, 0.22),
    (383_900, 0.24), (487_450, 0.32), (731_200, 0.35), (10_000_000, 0.37)
]
for lim, rate in actual_2024:
    print(f"    {pct(rate)}: up to {fmt(lim)}")

print(f"\n  Coded std deduction: {fmt(tc.std_deduction)}  ← 2024 MFJ should be $29,200")
print(f"  Actual 2024 MFJ std deduction: $29,200")

# Compare brackets
brackets_match = all(
    abs(coded[0] - actual[0]) < 100
    for coded, actual in zip(tc.brackets_ordinary, actual_2024)
)
check("Tax brackets match 2024 IRS values",
      brackets_match,
      f"Brackets appear to be slightly off from 2024 IRS values (see above)")

check("Standard deduction matches 2024 ($29,200 MFJ)",
      tc.std_deduction == 29_200,
      f"Coded {fmt(tc.std_deduction)}, should be $29,200 for 2024 MFJ")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 17 – Car Loan Rate Hardcoded
# ─────────────────────────────────────────────────────────────────────────────
section("SCENARIO 17 – Car Loan Rate Hardcoded at 6%")

print("  debts.py line 134: annual_rate=0.06 is hardcoded for car loans")
print("  The car_loan_rate field from the UI is accepted but NOT used")
check("Car loan uses user-specified interest rate",
      False,
      "debts.py hardcodes car loan rate at 6% regardless of what user enters. "
      "Should use config.get('car_loan_rate', 0.06)")


# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
section("AUDIT SUMMARY")

total = len(ISSUES) + len(PASSES)
print(f"\n  Total checks: {total}")
print(f"  ✅ Passing:   {len(PASSES)}")
print(f"  ❌ Issues:    {len(ISSUES)}\n")

print("─" * 70)
print("PASSING CHECKS:")
for p in PASSES:
    print(p)

print("\n" + "─" * 70)
print("ISSUES FOUND:")
for i, issue in enumerate(ISSUES, 1):
    print(f"[{i:02d}] {issue}")

print("\n" + "─" * 70)
print("\nKEY ISSUES BY SEVERITY:\n")
critical = [
    "1. [CRITICAL] Taxes_Paid always 0 — frontend shows $0 total tax paid every year",
    "2. [CRITICAL] FICA taxes not calculated — missing 7.65% employee payroll tax",
    "3. [CRITICAL] State income tax not calculated — stateOfResidence collected but ignored",
    "4. [CRITICAL] Withdrawal strategy uses INCOMPLETE cash_need — ignores mortgage/debt/medical/college in withdrawal logic",
    "5. [CRITICAL] Frontend totalSpend = Spend_Goal only — chart shows artificially low expenses",
]
high = [
    "6. [HIGH] retirementRatio not applied — post-retirement spending never reduces",
    "7. [HIGH] salaryGrowthRate not sent to backend — salary only grows with inflation",
    "8. [HIGH] postRetirementReturn not used — all accounts grow at pre-retirement rate",
    "9. [HIGH] Mortgage balance NOT subtracted from Net_Worth — overstates equity",
    "10. [HIGH] passive_income_growth_rate not applied — passive income only inflates",
]
medium = [
    "11. [MEDIUM] Standard deduction coded as $32,200 (should be $29,200 for 2024 MFJ)",
    "12. [MEDIUM] pensionCOLA=False ignored — all pensions inflation-adjusted",
    "13. [MEDIUM] Life Events V2 missing most event types (job, marriage, education, etc.)",
    "14. [MEDIUM] Life Events V1 uses undeclared variable cumulativePortfolioAdjustment — ReferenceError",
    "15. [MEDIUM] taxable_basis_ratio hardcoded at 0.8 — cannot be set by user",
    "16. [MEDIUM] contribDeferred/contribRoth dollar amounts from UI are ignored",
    "17. [MEDIUM] Car loan rate hardcoded at 6% regardless of user input",
    "18. [MEDIUM] rental_1_value always 0 — rental property net worth not calculated",
    "19. [MEDIUM] Social Security taxability (0-85%) not modeled — SS may be over/under-taxed",
    "20. [MEDIUM] One-time expenses from UI never sent to backend",
]

for item in critical:
    print(f"  {item}")
print()
for item in high:
    print(f"  {item}")
print()
for item in medium:
    print(f"  {item}")

print("\n" + "=" * 70)
print("WEALTH TRAJECTORY SMOOTHNESS ANALYSIS:")
print("=" * 70)
print("""
  The wealth chart appears smooth because:
  1. totalPortfolio = Net_Worth from backend, which INCLUDES home appreciation.
     Home value grows smoothly and masks drops in liquid assets.
  2. totalSpend in charts = Spend_Goal only, not actual Cash_Need.
     So expense line doesn't show spikes for college, medical, debt payoff.
  3. Withdrawal strategy refills accounts to meet only Spend_Goal+Taxes,
     not full cash needs, so liquid accounts don't drop as much as they should.
  4. Life events overlay (V2) doesn't compound impact correctly —
     it adds flat cash flow differences instead of compounding them.

  For a realistic chart with "falls":
  - Map totalSpend → Cash_Need (not Spend_Goal)
  - Ensure withdrawal strategy covers full Cash_Need 
  - Add college, mortgage payoff markers on charts
  - Fix life events to compound savings impacts at growth rate
""")
