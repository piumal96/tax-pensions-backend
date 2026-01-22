# Retirement Planner - Redesigned Version

## Overview
A simplified retirement planning simulator that models cash flows, taxes, and account growth for a married couple (P1 and P2) with individual work history until retirement.

## Key Features

### Account Structure
- **P1 Pre-Tax Account**: Individual IRA/401k for Person 1 with configurable growth rate
- **P2 Pre-Tax Account**: Individual IRA/401k for Person 2 with configurable growth rate
- **P1 Roth Account**: Individual Roth IRA for Person 1 with configurable growth rate
- **P2 Roth Account**: Individual Roth IRA for Person 2 with configurable growth rate
- **Joint Taxable Account**: Brokerage account accessible by both with configurable growth rate

### Income Sources (Per Person)
- **Employment Income**: Individual salary until specified retirement age
- **Social Security**: Individual amount at specified claiming age
- **Pensions**: Individual pension at specified start age
- **Required Minimum Distributions (RMDs)**: Calculated from pretax accounts at age 73+

### Withdrawal Strategy (Priority Order)
The simulator uses a step-by-step withdrawal approach:

1. **Employment Income**: First available cash from jobs
2. **Social Security**: Next level of retirement income
3. **Pensions**: Pension income if available
4. **Required Minimum Distributions (RMDs)**: Mandatory withdrawals from pretax accounts
   - Withdrawals taken from older person first
5. **Voluntary Pretax Withdrawals**: Additional withdrawals to meet cash need
   - Older person's account drawn first
6. **Taxable Account Withdrawals**: Joint brokerage account
7. **Roth Account Withdrawals**: Emergency withdrawals
   - Person 1 drawn first, then Person 2
8. **Roth Conversions**: Fill remaining bracket room at target tax rate
   - Convert from pretax accounts (older person first)

### Tax Tracking
- **Previous Year Taxes**: Tracked from year to year
- **Cash Need Calculation**: Spending goal + previous year taxes
- **Tax Calculation**: Federal taxes using 2024 brackets (MFJ)
  - Standard deduction applied to ordinary income
  - Capital gains stacked on top and taxed at preferential rates
  - Brackets adjusted annually for inflation

### Key Calculations

#### RMDs (Age 73+)
Uses IRS Uniform Lifetime Table with divisors from 26.5 at age 73 to 2.0 at age 120.

#### Tax Brackets (2024, adjusted for inflation)
- **Ordinary Income**: 10%, 12%, 22%, 24%, 32%, 35%, 37%
- **Long-Term Capital Gains**: 0%, 15%, 20%

#### Bracket Room for Conversions
Determines how much can be converted to Roth without exceeding target bracket rate.

## Configuration File (CSV Format)

### Parameters

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| p1_name | string | Husband | Name of Person 1 |
| p2_name | string | Wife | Name of Person 2 |
| p1_start_age | number | 65 | Person 1 current age |
| p2_start_age | number | 63 | Person 2 current age |
| end_simulation_age | number | 95 | Age when simulation ends (P1) |
| inflation_rate | decimal | 0.03 | Annual inflation rate (3%) |
| annual_spend_goal | number | 200000 | Annual spending goal in today's dollars |
| filing_status | string | MFJ | Tax filing status |
| **Employment** | | | |
| p1_employment_income | number | 100000 | P1 annual salary in today's dollars |
| p1_employment_until_age | number | 67 | P1 works until this age |
| p2_employment_income | number | 80000 | P2 annual salary in today's dollars |
| p2_employment_until_age | number | 65 | P2 works until this age |
| **Social Security** | | | |
| p1_ss_amount | number | 45000 | P1 annual SS in today's dollars |
| p1_ss_start_age | number | 70 | P1 claims SS at this age |
| p2_ss_amount | number | 45000 | P2 annual SS in today's dollars |
| p2_ss_start_age | number | 65 | P2 claims SS at this age |
| **Pensions** | | | |
| p1_pension | number | 0 | P1 annual pension in today's dollars |
| p1_pension_start_age | number | 67 | P1 pension start age |
| p2_pension | number | 0 | P2 annual pension in today's dollars |
| p2_pension_start_age | number | 65 | P2 pension start age |
| **Account Balances** | | | |
| bal_taxable | number | 700000 | Joint taxable (brokerage) balance |
| bal_pretax_p1 | number | 1250000 | P1 pre-tax balance |
| bal_pretax_p2 | number | 1250000 | P2 pre-tax balance |
| bal_roth_p1 | number | 60000 | P1 Roth balance |
| bal_roth_p2 | number | 60000 | P2 Roth balance |
| **Growth Rates** | | | |
| growth_rate_taxable | decimal | 0.07 | Annual return on taxable account (7%) |
| growth_rate_pretax_p1 | decimal | 0.07 | Annual return on P1 pre-tax (7%) |
| growth_rate_pretax_p2 | decimal | 0.07 | Annual return on P2 pre-tax (7%) |
| growth_rate_roth_p1 | decimal | 0.07 | Annual return on P1 Roth (7%) |
| growth_rate_roth_p2 | decimal | 0.07 | Annual return on P2 Roth (7%) |
| **Tax Settings** | | | |
| taxable_basis_ratio | decimal | 0.75 | Fraction of taxable withdrawal that is cost basis |
| target_tax_bracket_rate | decimal | 0.24 | Target bracket for Roth conversions (0.22, 0.24, or 0.32) |
| **Tax History** | | | |
| previous_year_taxes | number | 0 | Taxes paid in previous year |

## Output Columns

### Core Identification
- `Year`: Calendar year
- `P1_Age`: Person 1's age in this year
- `P2_Age`: Person 2's age in this year

### Income Sources
- `Employment_P1`: P1 employment income (if still working)
- `Employment_P2`: P2 employment income (if still working)
- `SS_P1`: P1 Social Security received
- `SS_P2`: P2 Social Security received
- `Pension_P1`: P1 pension received
- `Pension_P2`: P2 pension received
- `RMD_P1`: P1 required minimum distribution
- `RMD_P2`: P2 required minimum distribution
- `Total_Income`: Sum of all income sources

### Cash Flow
- `Spend_Goal`: Annual spending target (inflated)
- `Previous_Taxes`: Taxes paid in previous year
- `Cash_Need`: Spending goal + previous year taxes
- `WD_PreTax_P1`: Voluntary withdrawal from P1 pre-tax
- `WD_PreTax_P2`: Voluntary withdrawal from P2 pre-tax
- `WD_Taxable`: Withdrawal from joint taxable account
- `WD_Roth_P1`: Withdrawal from P1 Roth
- `WD_Roth_P2`: Withdrawal from P2 Roth
- `Roth_Conversion`: Total Roth conversion amount
- `Conv_P1`: Roth conversion from P1 pre-tax
- `Conv_P2`: Roth conversion from P2 pre-tax

### Taxes
- `Ord_Income`: Total ordinary income for tax purposes
- `Cap_Gains`: Capital gains from taxable account
- `Tax_Bill`: Federal income tax owed
- `Taxes_Paid`: Actual taxes paid from accounts

### Account Balances (End of Year)
- `Bal_PreTax_P1`: P1 pre-tax account balance
- `Bal_PreTax_P2`: P2 pre-tax account balance
- `Bal_Roth_P1`: P1 Roth account balance
- `Bal_Roth_P2`: P2 Roth account balance
- `Bal_Taxable`: Joint taxable account balance
- `Net_Worth`: Total of all accounts

## Usage

### Command Line
```bash
python retirement_planner_yr.py nisha.csv
```

### In Python
```python
from retirement_planner_yr import RetirementSimulator

sim = RetirementSimulator(config_file='nisha.csv', year=2025)
df = sim.run(verbose=True)

# Access specific results
print(df.iloc[0])  # First year
print(df[['Year', 'P1_Age', 'Net_Worth']])  # Specific columns
```

## Assumptions

1. **Inflation**: Applied uniformly to all income and spending (nominal values)
2. **Tax Brackets**: 2024 brackets adjusted annually for inflation
3. **Growth Rates**: Applied to beginning-of-year balance
4. **RMDs**: Withdrawn before voluntary withdrawals; taken from older person first
5. **Taxes**: Paid from taxable account first, then Roth accounts proportionally
6. **Roth Conversions**: Made after required withdrawals, filling remaining bracket room

## Design Simplifications

### Compared to Previous Version
- **Removed**: Strategy selection (A, B, C) - now uses optimal step-by-step approach
- **Removed**: Complex hybrid logic - replaced with clear priority order
- **Added**: Individual employment income with retirement ages
- **Added**: Previous year tax tracking for accurate cash need calculations
- **Added**: Individual growth rates per account (more flexibility)
- **Simplified**: Withdrawal logic is now transparent and follows financial best practices

### Not Modeled
- Healthcare costs or Medicare premiums
- State income taxes
- Net Investment Income Tax (NIIT)
- Charitable giving or AGI-sensitive deductions
- Asset location optimization beyond basic order
- Sequence of returns risk
- Longevity risk beyond fixed end age

## Files

- `retirement_planner_yr.py`: Main simulator class
- `nisha.csv`: Example configuration with baseline scenario
- `sim_nisha.csv`: Output of example run
- `__INDEX.md`: Project index
- `requirements.txt`: Python dependencies

## Dependencies

- pandas >= 1.5.0
- numpy >= 1.21.0

## Example Output

```
====================================================================================================
RETIREMENT SIMULATION SUMMARY (values in thousands)
====================================================================================================
 Year  P1_Age  P2_Age  Total_Income  Cash_Need  Ord_Income  Tax_Bill  Net_Worth
 2026      65      63         180.0      200.0       435.8      82.0     3450.4
 2027      66      64         185.4      288.0       448.8      84.5     3504.7
 ...
 2056      95      93         218.5      500.6       218.5      15.6     1401.7
```

## Notes

- The simulator runs from `p1_start_age` until `end_simulation_age`
- Employment income ends when the person reaches their employment_until_age
- Social Security is claimed at their specified start age
- RMDs begin at age 73 and use IRS Uniform Lifetime Table
- Previous year taxes are tracked and added to cash need each year
- Roth conversions happen after all other withdrawals to fill remaining bracket room
