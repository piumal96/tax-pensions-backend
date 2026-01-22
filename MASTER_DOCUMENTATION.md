# Retirement Planner: Business Logic Specification

This document defines the exact **Input**, **Process**, and **Output** of the retirement planning logic. It contains no code or technical details, only business rules.

---

# 1. EXACT INPUTS (All 33 Parameters)
These are the specific data points required in the CSV to run the calculation.

### A. Personal Details (5 Items)
| Exact Parameter Key | Description |
| :--- | :--- |
| **`p1_name`** | Name of Husband/Partner 1. |
| **`p2_name`** | Name of Wife/Partner 2. |
| **`p1_start_age`** | The starting age for Person 1. |
| **`p2_start_age`** | The starting age for Person 2. |
| **`filing_status`** | Tax filing status (e.g., "MFJ"). |

### B. Simulation Settings (2 Items)
| Exact Parameter Key | Description |
| :--- | :--- |
| **`end_simulation_age`** | The simulation stops when P1 hits this age. |
| **`inflation_rate`** | Annual inflation rate (e.g. 0.03). |

### C. Financial Goals & History (3 Items)
| Exact Parameter Key | Description |
| :--- | :--- |
| **`annual_spend_goal`** | Desired annual spending in *Today's Dollars*. |
| **`target_tax_bracket_rate`**| STRATEGY: Max tax rate for Roth Conversions. |
| **`previous_year_taxes`** | The tax bill owed from the year before simulation starts. |

### D. Income Streams (12 Items)
| Exact Parameter Key | Description |
| :--- | :--- |
| **`p1_employment_income`** | P1 Annual Salary. |
| **`p1_employment_until_age`**| Age P1 stops working. |
| **`p2_employment_income`** | P2 Annual Salary. |
| **`p2_employment_until_age`**| Age P2 stops working. |
| **`p1_ss_amount`** | P1 Annual Social Security. |
| **`p1_ss_start_age`** | Age P1 Social Security starts. |
| **`p2_ss_amount`** | P2 Annual Social Security. |
| **`p2_ss_start_age`** | Age P2 Social Security starts. |
| **`p1_pension`** | P1 Annual Pension. |
| **`p1_pension_start_age`** | Age P1 Pension starts. |
| **`p2_pension`** | P2 Annual Pension. |
| **`p2_pension_start_age`** | Age P2 Pension starts. |

### E. Assets & Growth (11 Items)
| Exact Parameter Key | Description |
| :--- | :--- |
| **`bal_taxable`** | Brokerage Account Balance. |
| **`bal_pretax_p1`** | P1 401k/IRA Balance. |
| **`bal_pretax_p2`** | P2 401k/IRA Balance. |
| **`bal_roth_p1`** | P1 Roth Balance. |
| **`bal_roth_p2`** | P2 Roth Balance. |
| **`growth_rate_taxable`** | Annual Return for Brokerage. |
| **`growth_rate_pretax_p1`** | Annual Return for P1 PreTax. |
| **`growth_rate_pretax_p2`** | Annual Return for P2 PreTax. |
| **`growth_rate_roth_p1`** | Annual Return for P1 Roth. |
| **`growth_rate_roth_p2`** | Annual Return for P2 Roth. |
| **`taxable_basis_ratio`** | % of Brokerage that is Principal. |

---

# 2. EXACT PROCESS (The Calculations)
The system runs a loop for every year (Example: 2026 to 2055). Inside that loop, it follows this **exact** sequence:

### Step 1: Apply Investment Growth (First Thing)
Every account grows *before* any money is taken out for the year.
*   `Taxable Balance` = `Current Balance` * `(1 + Rate)`
*   `PreTax Balance` = `Current Balance` * `(1 + Rate)`
*   `Roth Balance` = `Current Balance` * `(1 + Rate)`

### Step 2: Calculate Fixed Income
Check if the person is old enough to trigger payments (inflation adjusted).
*   **Employment**: IF `Age < Works_Until_Age` THEN `Income = Salary`. ELSE `0`.
*   **Social Security**: IF `Age >= SS_Start_Age` THEN `Income = SS_Amount`. ELSE `0`.
*   **Pension**: IF `Age >= Pension_Start_Age` THEN `Income = Pension`. ELSE `0`.

### Step 3: Calculate RMDs (Forced Widthrawals)
The government forces you to withdraw from Pre-Tax accounts.
*   **Check**: IF `Age >= 73`:
    *   `Factor` = Look up Age in IRS Uniform Lifetime Table (e.g., 26.5 @ 73).
    *   `RMD Amount` = `PreTax Balance` / `Factor`.
*   **Action**: This money is forcibly removed from the PreTax Account Buffer and added to "Income".

### Step 4: Calculate Cash Need (The Bill)
*   `Inflation Factor` = `(1 + InflationRate) ^ Years`.
*   `Current Spend Goal` = `Annual Spend Goal` * `Inflation Factor`.
*   **`Total Cash Need`** = `Current Spend Goal` + `Last Year's Tax Bill`.

### Step 5: Solve the Shortfall (The Waterfall)
**`Shortfall`** = `Total Cash Need` - (`Salary` + `SS` + `Pension` + `RMDs`).

IF `Shortfall > 0`, withdraw assets in this priority:
1.  **Pre-Tax (Older First)**: Withdraw from the *Older Spouse's* IRA first. Then the Younger.
2.  **Taxable Brokerage**: If Pre-Tax is empty, sell Brokerage assets.
3.  **Roth (Older First)**: If Brokerage is empty, withdraw from Roth.

### Step 6: Strategy - Roth Conversion
Check if we should move money to "fill" the tax bracket.
*   `Current Ordinary Income` = `Salary` + `SS` + `Pension` + `RMDs` + `PreTax Analysis`.
*   `Bracket Limit` = The income limit for your target rate (e.g. $403,550 for 24%).
*   **`Conversion Room`** = `Bracket Limit` - `Current Ordinary Income`.
*   **Action**: IF `Room > 0`, move that amount from `PreTax` -> `Roth`. (Older spouse first).

### Step 7: Calculate Taxes (For Next Year)
Calculate the bill to be paid in the *next* loop.
*   `Ordinary Income` = `Salary` + `SS` + `Pension` + `RMDs` + `PreTax WD` + `Conversions`.
*   `Capital Gains` = `Taxable WD` * `(1 - BasisRatio)`.
*   **Math**: Apply 2024 Federal Tax Brackets to (`Ordinary` + `Gains`).
*   **Save**: Store this `Tax_Bill` for Step 4 of the next year.

---

# 3. EXACT OUTPUTS (All 33 Columns)
This is the complete list of columns generated in the output file, in exact order.

### A. Timeline (When)
1.  **`Year`**: The calendar year (e.g., 2026).
2.  **`P1_Age`**: Husband's age.
3.  **`P2_Age`**: Wife's age.

### B. Income Sources (Money In)
4.  **`Employment_P1`**: Husband's salary.
5.  **`Employment_P2`**: Wife's salary.
6.  **`SS_P1`**: Husband's Social Security.
7.  **`SS_P2`**: Wife's Social Security.
8.  **`Pension_P1`**: Husband's Pension.
9.  **`Pension_P2`**: Wife's Pension.
10. **`RMD_P1`**: Husband's Required Minimum Distribution (from Pre-Tax).
11. **`RMD_P2`**: Wife's Required Minimum Distribution (from Pre-Tax).
12. **`Total_Income`**: Sum of all items 4-11.

### C. Cash Requirements (Bills)
13. **`Spend_Goal`**: Your desired spending (inflation adjusted).
14. **`Previous_Taxes`**: The tax bill owed from the previous year.
15. **`Cash_Need`**: Total cash required (`Spend_Goal` + `Previous_Taxes`).

### D. Withdrawals (To Pay Bills)
16. **`WD_PreTax_P1`**: Amount taken from Husband's IRA/401k.
17. **`WD_PreTax_P2`**: Amount taken from Wife's IRA/401k.
18. **`WD_Taxable`**: Amount taken from Brokerage Account.
19. **`WD_Roth_P1`**: Amount taken from Husband's Roth.
20. **`WD_Roth_P2`**: Amount taken from Wife's Roth.

### E. Strategy (Tax Moves)
21. **`Roth_Conversion`**: Total money converted from Pre-Tax to Roth.
22. **`Conv_P1`**: Portion coming from Husband's Pre-Tax account.
23. **`Conv_P2`**: Portion coming from Wife's Pre-Tax account.

### F. Taxes (The Math)
24. **`Ord_Income`**: Ordinary Income (Wages + SS + RMD + Conversions).
25. **`Cap_Gains`**: Capital Gains (Profit from Taxable Withdrawals).
26. **`Tax_Bill`**: The Federal Tax Calculated for this year.
27. **`Taxes_Paid`**: (Legacy Placeholder) Always 0. Taxes are paid via `Cash_Need` next year.

### G. Balances (Wealth)
28. **`Bal_PreTax_P1`**: Husband's ending Pre-Tax Balance.
29. **`Bal_PreTax_P2`**: Wife's ending Pre-Tax Balance.
30. **`Bal_Roth_P1`**: Husband's ending Roth Balance.
31. **`Bal_Roth_P2`**: Wife's ending Roth Balance.
32. **`Bal_Taxable`**: Joint Brokerage ending Balance.
33. **`Net_Worth`**: Total Sum of Columns 28-32.
