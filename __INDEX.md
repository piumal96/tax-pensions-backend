# Retirement Planner - Project Index

## Quick Start
```bash
python retirement_planner_yr.py nisha.csv
```

## Files

### Code
- **retirement_planner_yr.py** (432 lines)
  - Main simulator class: `RetirementSimulator`
  - Key methods:
    - `__init__()`: Load configuration and tax/RMD tables
    - `run()`: Execute year-by-year simulation
    - `calculate_tax()`: Federal income tax calculation with capital gains stacking
    - `get_bracket_room()`: Calculate Roth conversion capacity
    - `get_rmd_factor()`: Look up RMD divisor by age

### Configuration
- **nisha.csv**
  - Baseline scenario: married couple (ages 65/63) with individual employment income until retirement
  - Key values:
    - Account balances: $700k taxable, $1.25M each pretax, $60k each Roth
    - Employment: P1 $100k to age 67, P2 $80k to age 65
    - SS: $45k each at ages 70/65
    - Spending goal: $200k/year
    - Growth rate: 7% all accounts
    - Target tax bracket: 24%

### Output
- **sim_nisha.csv**
  - Results of running nisha.csv scenario (ages 65-95, 31 years)
  - Columns: 30 metrics per year including income, withdrawals, taxes, balances

### Documentation
- **README.md**
  - Comprehensive guide: overview, features, configuration, usage
  - All input parameters documented
  - Output columns explained
  - Assumptions and design notes

- **__INDEX.md** (this file)
  - Project structure and file reference

## Architecture

### Data Flow
1. Load CSV config → Parse numeric values
2. Initialize account balances, inflation, tax tables
3. For each year until end_age:
   - Apply growth to accounts
   - Calculate all income sources
   - Determine RMDs
   - Calculate cash need = spending + previous_year_taxes
   - Execute step-by-step withdrawals (employment → SS → pension → RMD → pretax → taxable → roth)
   - Execute Roth conversions (fill remaining bracket room)
   - Calculate federal taxes
   - Pay taxes from available accounts
   - Record all metrics
4. Export results to CSV, display summary

### Key Algorithms

#### Withdrawal Priority (when shortfall exists)
```
1. Employment income (auto-deposited)
2. Social Security (auto-deposited)
3. Pensions (auto-deposited)
4. RMDs (forced withdrawal)
5. Voluntary pretax (older person first)
6. Taxable account
7. Roth accounts (P1 first, then P2)
```

#### Roth Conversion
```
1. Calculate ordinary income after all other withdrawals
2. Determine bracket room (gap to target bracket limit)
3. Convert available pretax (older person first) up to bracket room
4. Add conversions to respective Roth accounts
```

#### Tax Calculation
```
1. Adjust brackets and standard deduction for inflation
2. Apply standard deduction to ordinary income
3. Calculate tax on ordinary income using progressive brackets
4. Stack capital gains on top, calculate tax at preferential rates
5. Sum ordinary income tax + capital gains tax
```

## Customization

### Create New Scenario
```python
# Copy nisha.csv to new_scenario.csv
# Edit parameters (accounts, income, ages, etc)
# Run: python retirement_planner_yr.py new_scenario.csv
```

### Modify Assumptions
- **Tax rates**: Edit `brackets_ordinary`, `brackets_ltcg` in `__init__`
- **RMD factors**: Edit `rmd_table` in `__init__`
- **Standard deduction**: Edit `self.std_deduction` in `__init__`
- **Withdrawal logic**: Edit `run()` method's withdrawal section

### Integration
```python
from retirement_planner_yr import RetirementSimulator

# Create scenario
sim = RetirementSimulator('my_scenario.csv')

# Run simulation
results = sim.run(verbose=False)

# Analyze results
final_balance = results.iloc[-1]['Net_Worth']
peak_balance = results['Net_Worth'].max()
```

## Key Parameters Explained

### Ages
- Individuals retire at different ages (employment_until_age)
- RMDs begin at 73
- Simulation ends at end_simulation_age (based on P1)

### Growth Rates
- Applied at beginning of year
- Can differ per account and person
- Accounts compound annually at specified rate

### Withdrawal Priority
- Older person's pretax drawn before younger person
- Younger person can still work while older person retires
- Accounts individually tracked for each person

### Tax Bracket Targeting
- After meeting cash needs, remaining pretax converted to Roth
- Conversions limited to maintain target bracket (usually 24%)
- Prevents unexpected higher taxes in future
- Can convert up to brackets 22%, 24%, or 32%

## Example Scenarios

### Early Retiree
```
p1_employment_until_age,62
p2_employment_until_age,60
(Both retire early, higher initial withdrawals needed)
```

### Delayed Claiming
```
p1_ss_start_age,75  (increased SS amount)
p2_ss_start_age,70  (increased SS amount)
(Lower early withdrawals, higher later incomes)
```

### High Income
```
annual_spend_goal,400000
p1_employment_income,200000
p2_employment_income,150000
(More aggressive Roth conversions possible)
```

## Testing

Run the baseline scenario:
```bash
cd c:\Users\yasan\python\retirement_planner
python retirement_planner_yr.py nisha.csv
```

Expected output:
- CSV file: sim_nisha.csv created
- Console summary showing 31 years of projections
- Net worth declining from ~$3.5M to ~$1.4M (due to withdrawals exceeding growth)

## Future Enhancements

Possible additions (not currently implemented):
- State income tax
- Healthcare cost projections
- Social Security wage indexing formulas
- NIIT (3.8%) on investment income
- Charitable bunching strategies
- Asset location optimization
- Monte Carlo simulation for sequence of returns
- Integration with web UI (Flask app already present)

## Version History

- **Current (2026)**: Simplified redesign
  - Clean step-by-step withdrawal logic
  - Individual accounts per person
  - Previous year tax tracking
  - Clear configuration structure
  
- **Previous**: Complex strategy selection (A, B, C)
  - Multiple competing algorithms
  - Grouped accounts per type
  - Harder to understand and debug
