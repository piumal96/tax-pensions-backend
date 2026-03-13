import numpy as np
from engine.real_estate import Mortgage
from engine.debts import initialize_debts, process_all_debt_payments, get_total_debt_balance
from engine.taxes import TaxCalculator, SS_EXEMPT_STATES
from engine.withdrawals import StandardStrategy, TaxableFirstStrategy


class SimulationConfig:
    """
    Pure data holder for simulation configuration.
    Validation lives in the schemas layer.
    """
    def __init__(self, start_year=2025, **kwargs):
        self.start_year = start_year
        self.inputs = kwargs

    def get(self, key, default=0):
        return self.inputs.get(key, default)

    def __getitem__(self, key):
        return self.inputs[key]


def get_rmd_factor(age, rmd_table):
    """RMD uniform-lifetime divisor for age."""
    if age < 73:
        return 0
    if age >= 120:
        return 2.0
    return rmd_table.get(age, max(2.0, 27.4 - (age - 72)))


def initialize_mortgages(config):
    """Initialize primary and rental mortgages from config."""
    primary = None
    rentals = {}

    principal = config.get('primary_home_mortgage_principal', 0)
    rate = config.get('primary_home_mortgage_rate', 0)
    if rate > 1:
        rate /= 100
    years = config.get('primary_home_mortgage_years', 0)
    if principal > 0 and years > 0:
        primary = Mortgage(principal, rate, years)

    i = 1
    while True:
        key = f'rental_{i}_mortgage_principal'
        if key not in config.inputs:
            break
        rp = config.get(key, 0)
        rr = config.get(f'rental_{i}_mortgage_rate', 0)
        if rr > 1:
            rr /= 100
        ry = config.get(f'rental_{i}_mortgage_years', 0)
        if rp > 0 and ry > 0:
            rentals[i] = Mortgage(rp, rr, ry)
        i += 1

    return primary, rentals


def run_deterministic(config: SimulationConfig, strategy_name: str = 'standard',
                      volatility: float = 0.0):
    """
    Year-by-year deterministic simulation (the core calculation engine).

    Fixed in this version:
    - 2024 federal tax brackets & standard deduction
    - FICA payroll tax on wages
    - State income tax
    - Social Security taxability (0 / 50 / 85 % formula)
    - Mortgage balance subtracted from net worth
    - Retirement spending ratio applied after retirement
    - Salary growth at user-specified rate (not just inflation)
    - Post-retirement portfolio growth rate
    - passive_income_growth_rate actually grows passive income
    - pensionCOLA flag respected
    - Taxes_Paid recorded correctly (what was actually paid this year)
    - Full cash_need passed to withdrawal strategy
    - One-time expenses supported
    """

    tax_calc = TaxCalculator()
    strategy = TaxableFirstStrategy() if strategy_name == 'taxable_first' else StandardStrategy()

    # RMD Uniform-Lifetime table (SECURE 2.0 — RMDs start at 73)
    rmd_table = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1,
        80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2,
        87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1,
        94: 9.5,  95: 8.9,  96: 8.4,  97: 7.8,  98: 7.3,  99: 6.8, 100: 6.4,
        101: 6.0, 102: 5.6, 103: 5.2, 104: 4.9, 105: 4.6, 106: 4.3, 107: 4.1,
        108: 3.9, 109: 3.7, 110: 3.5, 111: 3.4, 112: 3.3, 113: 3.1, 114: 3.0,
        115: 2.9, 116: 2.8, 117: 2.7, 118: 2.5, 119: 2.3, 120: 2.0,
    }

    primary_mortgage, rental_mortgages = initialize_mortgages(config)
    debts = initialize_debts(config)

    # ── Rates & constants ───────────────────────────────────────────────────
    inflation_rate = config['inflation_rate']
    state = config.get('state_of_residence', 'Texas')
    retirement_spending_ratio = config.get('retirement_spending_ratio', 0.80)

    # Growth rates
    pre_growth_taxable   = config['growth_rate_taxable']
    pre_growth_pretax_p1 = config['growth_rate_pretax_p1']
    pre_growth_pretax_p2 = config['growth_rate_pretax_p2']
    pre_growth_roth_p1   = config['growth_rate_roth_p1']
    pre_growth_roth_p2   = config['growth_rate_roth_p2']
    post_growth          = config.get('post_retirement_growth_rate', 0.05)

    # Salary growth (default to inflation if not set)
    p1_salary_growth = config.get('p1_salary_growth_rate', inflation_rate)
    p2_salary_growth = config.get('p2_salary_growth_rate', inflation_rate)
    p1_salary_current = config['p1_employment_income']
    p2_salary_current = config['p2_employment_income']

    # Medical
    medical_inflation_idx = 1.0
    medical_inflation_rate = config.get('medical_inflation_rate', 0.06)

    # Business
    business_income_current = config.get('business_income', 0)
    business_growth_rate    = config.get('business_growth_rate', 0.03)
    business_ends_at_age    = config.get('business_ends_at_age', 65)

    # Passive income (grows at its own rate, not inflation)
    passive_income_current      = config.get('passive_income', 0)
    passive_income_growth_rate  = config.get('passive_income_growth_rate', 0.02)

    # Rent
    monthly_rent      = config.get('monthly_rent', 0)
    rent_inflation_rate = config.get('rent_inflation_rate', 0.03)
    annual_rent       = monthly_rent * 12

    # Life insurance
    li_premium  = config.get('life_insurance_premium', 0)
    li_type     = config.get('life_insurance_type', 'none')
    li_term_end = config.get('life_insurance_term_ends_at_age', 65)

    # Children
    num_children = config.get('num_children', 0)
    child_ages   = [config.get(f'child_{i}_current_age', 0) for i in range(1, num_children + 1)]
    exp_0_5      = config.get('monthly_expense_per_child_0_5',   500)
    exp_6_12     = config.get('monthly_expense_per_child_6_12',  800)
    exp_13_17    = config.get('monthly_expense_per_child_13_17', 1000)
    college_cost = config.get('college_cost_per_year', 25_000)

    # One-time expenses  [{year: int, amount: float, description: str}]
    one_time_expenses = config.get('one_time_expenses', []) or []

    # Real estate
    primary_home_value      = config.get('primary_home_value', 0)
    primary_home_growth     = config.get('primary_home_growth_rate', inflation_rate)
    rental_assets = []
    i = 1
    while True:
        vk = f'rental_{i}_value'
        if vk not in config.inputs:
            break
        rental_assets.append({
            'id': i,
            'value':             config.inputs[vk],
            'income':            config.get(f'rental_{i}_income', 0),
            'growth_rate':       config.get(f'rental_{i}_growth_rate', inflation_rate),
            'income_growth_rate':config.get(f'rental_{i}_income_growth_rate', inflation_rate),
        })
        i += 1

    # ── Initial state ───────────────────────────────────────────────────────
    inflation_idx   = 1.0
    p1_age          = int(config['p1_start_age'])
    p2_age          = int(config['p2_start_age'])
    end_age         = int(config['end_simulation_age'])
    p1_retire_age   = int(config['p1_employment_until_age'])

    b_taxable    = config['bal_taxable']
    b_pretax_p1  = config['bal_pretax_p1']
    b_pretax_p2  = config['bal_pretax_p2']
    b_roth_p1    = config['bal_roth_p1']
    b_roth_p2    = config['bal_roth_p2']

    # Taxes paid in the PREVIOUS year (used for this year's cash_need)
    taxes_paid_prev_year = config.get('previous_year_taxes', 0)

    records = []
    year    = config.start_year

    # ── MAIN SIMULATION LOOP ────────────────────────────────────────────────
    while p1_age <= end_age:
        year += 1
        is_retired = p1_age >= p1_retire_age

        # ── 1. Account Growth ───────────────────────────────────────────────
        market_adj = np.random.normal(0, volatility) if volatility > 0 else 0.0

        if is_retired:
            g_taxable = g_pretax_p1 = g_pretax_p2 = g_roth_p1 = g_roth_p2 = post_growth
        else:
            g_taxable   = pre_growth_taxable
            g_pretax_p1 = pre_growth_pretax_p1
            g_pretax_p2 = pre_growth_pretax_p2
            g_roth_p1   = pre_growth_roth_p1
            g_roth_p2   = pre_growth_roth_p2

        b_taxable   *= (1 + g_taxable   + market_adj)
        b_pretax_p1 *= (1 + g_pretax_p1 + market_adj)
        b_pretax_p2 *= (1 + g_pretax_p2 + market_adj)
        b_roth_p1   *= (1 + g_roth_p1   + market_adj)
        b_roth_p2   *= (1 + g_roth_p2   + market_adj)

        primary_home_value *= (1 + primary_home_growth)

        current_rental_income = 0.0
        current_rental_value_total = 0.0
        for rental in rental_assets:
            rental['value'] *= (1 + rental['growth_rate'])
            current_rental_value_total += rental['value']
            if rental['income'] == 0 and rental['value'] > 0:
                current_rental_income += (rental['value'] / 500_000) * 2_000 * 12
            else:
                rental['income'] *= (1 + rental['income_growth_rate'])
                current_rental_income += rental['income']

        # ── 2. Income ───────────────────────────────────────────────────────
        emp_p1 = p1_salary_current if p1_age < p1_retire_age else 0.0
        emp_p2 = p2_salary_current if p2_age < config['p2_employment_until_age'] else 0.0

        ss_p1 = config['p1_ss_amount'] * inflation_idx if p1_age >= config['p1_ss_start_age'] else 0.0
        ss_p2 = config['p2_ss_amount'] * inflation_idx if p2_age >= config['p2_ss_start_age'] else 0.0
        ss_total = ss_p1 + ss_p2

        pens_p1 = 0.0
        if p1_age >= config['p1_pension_start_age']:
            cola_p1 = config.get('p1_pension_cola', True)
            pens_p1 = config['p1_pension'] * (inflation_idx if cola_p1 else 1.0)

        pens_p2 = 0.0
        if p2_age >= config['p2_pension_start_age']:
            cola_p2 = config.get('p2_pension_cola', True)
            pens_p2 = config['p2_pension'] * (inflation_idx if cola_p2 else 1.0)

        pens_total = pens_p1 + pens_p2

        business_income_this_year = 0.0
        if p1_age < business_ends_at_age and business_income_current > 0:
            business_income_this_year = business_income_current
            business_income_current *= (1 + business_growth_rate)

        passive_income_this_year = passive_income_current

        # ── 3. RMDs ─────────────────────────────────────────────────────────
        rmd_p1 = 0.0
        if p1_age >= 73 and b_pretax_p1 > 0:
            f = get_rmd_factor(p1_age, rmd_table)
            if f > 0:
                rmd_p1 = b_pretax_p1 / f

        rmd_p2 = 0.0
        if p2_age >= 73 and b_pretax_p2 > 0:
            f = get_rmd_factor(p2_age, rmd_table)
            if f > 0:
                rmd_p2 = b_pretax_p2 / f

        rmd_total = rmd_p1 + rmd_p2

        # ── 4. Fixed Outflows ───────────────────────────────────────────────
        # Mortgages
        total_mortgage_payment = 0.0
        if primary_mortgage and not primary_mortgage.is_paid_off():
            primary_mortgage.make_payment(12)
            total_mortgage_payment += primary_mortgage.get_annual_payment()
        for rid, m in rental_mortgages.items():
            if not m.is_paid_off():
                m.make_payment(12)
                total_mortgage_payment += m.get_annual_payment()

        # Debts
        total_debt_payment, debt_interest_paid, remaining_debt = process_all_debt_payments(debts, 12)

        # Medical
        medical_expenses_this_year = config.get('annual_medical_expenses', 0) * medical_inflation_idx
        medical_inflation_idx *= (1 + medical_inflation_rate)

        # Rent
        rent_this_year = 0.0
        if monthly_rent > 0:
            rent_this_year = annual_rent
            annual_rent *= (1 + rent_inflation_rate)

        # Life insurance
        insurance_premium_this_year = 0.0
        if li_type != 'none' and li_premium > 0:
            if li_type == 'term':
                if p1_age < li_term_end:
                    insurance_premium_this_year = li_premium * 12
            else:
                insurance_premium_this_year = li_premium * 12

        # Children & college
        child_expenses_this_year   = 0.0
        college_expenses_this_year = 0.0
        for idx, child_age in enumerate(child_ages):
            if child_age < 18:
                if child_age <= 5:
                    child_expenses_this_year += exp_0_5 * 12
                elif child_age <= 12:
                    child_expenses_this_year += exp_6_12 * 12
                else:
                    child_expenses_this_year += exp_13_17 * 12
            elif 18 <= child_age < 22:
                college_expenses_this_year += college_cost
            child_ages[idx] += 1

        # One-time expenses for this calendar year
        one_time_this_year = sum(
            float(e.get('amount', 0))
            for e in one_time_expenses
            if e.get('year') == year
        )

        # Spend goal: reduced in retirement by spending ratio
        base_spend = config['annual_spend_goal'] * inflation_idx
        spend_goal = base_spend * retirement_spending_ratio if is_retired else base_spend

        # Full cash need (used for both withdrawal strategy AND reporting)
        cash_need = (spend_goal
                     + total_mortgage_payment
                     + taxes_paid_prev_year          # last year's tax bill
                     + total_debt_payment
                     + medical_expenses_this_year
                     + rent_this_year
                     + insurance_premium_this_year
                     + child_expenses_this_year
                     + college_expenses_this_year
                     + one_time_this_year)

        # ── 5. Withdrawals ──────────────────────────────────────────────────
        strategy_inputs = {
            'p1_age': p1_age,
            'p2_age': p2_age,
            'spend_goal': spend_goal,
            'previous_year_taxes':     taxes_paid_prev_year,
            'mortgage_payment':        total_mortgage_payment,
            'debt_payment':            total_debt_payment,
            'medical_expenses':        medical_expenses_this_year,
            'child_expenses':          child_expenses_this_year,
            'college_expenses':        college_expenses_this_year,
            'rent':                    rent_this_year,
            'insurance':               insurance_premium_this_year,
            'one_time_expenses':       one_time_this_year,
            'target_tax_bracket_rate': config['target_tax_bracket_rate'],
        }

        s_res = strategy.execute(
            strategy_inputs,
            (b_taxable, b_pretax_p1, b_pretax_p2, b_roth_p1, b_roth_p2),
            (emp_p1, emp_p2, ss_total, pens_total, rmd_p1, rmd_p2),
            inflation_idx,
            rmd_table,
            tax_calc.brackets_ordinary,
            tax_calc.std_deduction,
        )

        wd_pretax_p1  = s_res['wd_pretax_p1']
        wd_pretax_p2  = s_res['wd_pretax_p2']
        wd_taxable    = s_res['wd_taxable']
        wd_roth_p1    = s_res['wd_roth_p1']
        wd_roth_p2    = s_res['wd_roth_p2']
        roth_conversion = s_res['roth_conversion']
        conv_p1       = s_res['conv_p1']
        conv_p2       = s_res['conv_p2']

        total_income = (emp_p1 + emp_p2 + ss_total + pens_total + rmd_total
                        + current_rental_income + business_income_this_year
                        + passive_income_this_year)

        # ── 6. Update Balances — Withdrawals ───────────────────────────────
        b_pretax_p1 -= (rmd_p1 + wd_pretax_p1 + conv_p1)
        b_pretax_p2 -= (rmd_p2 + wd_pretax_p2 + conv_p2)
        b_roth_p1   += conv_p1
        b_roth_p1   -= wd_roth_p1
        b_roth_p2   += conv_p2
        b_roth_p2   -= wd_roth_p2
        b_taxable   -= wd_taxable

        # ── 7. Accumulation Phase: Invest Surplus ───────────────────────────
        contrib_p1_401k = 0.0
        contrib_p2_401k = 0.0
        match_p1        = 0.0
        match_p2        = 0.0
        contrib_strategy_used = 'None'

        total_cash_income  = (emp_p1 + emp_p2 + ss_total + pens_total
                              + current_rental_income + business_income_this_year
                              + passive_income_this_year)
        total_cash_needed  = (spend_goal + total_mortgage_payment + taxes_paid_prev_year
                              + total_debt_payment + medical_expenses_this_year
                              + rent_this_year + insurance_premium_this_year
                              + child_expenses_this_year + college_expenses_this_year
                              + one_time_this_year)
        cash_surplus = total_cash_income - total_cash_needed

        if cash_surplus > 0:
            p1_contrib_rate = config.get('p1_401k_contribution_rate', 0.15)
            p2_contrib_rate = config.get('p2_401k_contribution_rate', 0.15)
            p1_match_rate   = config.get('p1_401k_employer_match_rate', 0.05)
            p2_match_rate   = config.get('p2_401k_employer_match_rate', 0.05)
            p1_force_roth   = config.get('p1_401k_is_roth', False)
            p2_force_roth   = config.get('p2_401k_is_roth', False)
            auto_optimize   = config.get('auto_optimize_roth_traditional', True)

            adj_std_ded = tax_calc.std_deduction * inflation_idx
            taxable_income = max(0.0, total_cash_income - adj_std_ded)
            adj_brackets = [(lim * inflation_idx, rate) for lim, rate in tax_calc.brackets_ordinary]
            current_marginal_rate = 0.24
            for limit, rate in adj_brackets:
                if taxable_income <= limit:
                    current_marginal_rate = rate
                    break

            target_rate     = config.get('target_tax_bracket_rate', 0.24)
            remaining_surplus = cash_surplus

            if p1_age < p1_retire_age and emp_p1 > 0:
                max_p1 = 30_500 if p1_age >= 50 else 23_000
                ec_p1  = min(emp_p1 * p1_contrib_rate, max_p1, remaining_surplus)
                contrib_p1_401k = ec_p1
                match_p1 = min(emp_p1 * p1_match_rate, max_p1)
                use_roth_p1 = p1_force_roth or (auto_optimize and current_marginal_rate <= target_rate)
                if use_roth_p1:
                    b_roth_p1 += (ec_p1 + match_p1)
                    contrib_strategy_used = 'Roth'
                else:
                    b_pretax_p1 += (ec_p1 + match_p1)
                    contrib_strategy_used = 'Traditional'
                remaining_surplus -= ec_p1

            if p2_age < config['p2_employment_until_age'] and emp_p2 > 0 and remaining_surplus > 0:
                max_p2 = 30_500 if p2_age >= 50 else 23_000
                ec_p2  = min(emp_p2 * p2_contrib_rate, max_p2, remaining_surplus)
                contrib_p2_401k = ec_p2
                match_p2 = min(emp_p2 * p2_match_rate, max_p2)
                use_roth_p2 = config.get('p2_401k_is_roth', False) or \
                              (auto_optimize and current_marginal_rate <= target_rate)
                if use_roth_p2:
                    b_roth_p2 += (ec_p2 + match_p2)
                else:
                    b_pretax_p2 += (ec_p2 + match_p2)
                remaining_surplus -= ec_p2

            if remaining_surplus > 0:
                after_tax = remaining_surplus * (1 - current_marginal_rate)
                b_taxable += after_tax

        # ── 8. Tax Calculation ──────────────────────────────────────────────
        # Social Security taxability (provisional income formula)
        non_ss_income = (emp_p1 + emp_p2 + pens_total + rmd_total
                         + wd_pretax_p1 + wd_pretax_p2 + roth_conversion
                         + current_rental_income + business_income_this_year
                         + passive_income_this_year)
        provisional_income = non_ss_income + 0.5 * ss_total
        taxable_ss = tax_calc.taxable_social_security(ss_total, provisional_income)

        final_ord_income = non_ss_income + taxable_ss

        basis_ratio  = config['taxable_basis_ratio']
        capital_gains = wd_taxable * (1 - basis_ratio)

        federal_tax = tax_calc.calculate_federal_tax(final_ord_income, capital_gains, inflation_idx)

        # FICA on wages only
        fica_tax = tax_calc.calculate_fica(emp_p1, emp_p2)

        # State income tax
        ss_state_exempt = ss_total if state in SS_EXEMPT_STATES else 0.0
        state_tax = tax_calc.calculate_state_tax(
            final_ord_income, state, inflation_idx, exclude_ss=ss_state_exempt
        )

        total_tax_bill = federal_tax + fica_tax + state_tax

        # taxes_paid_prev_year is what was USED in cash_need this year
        # total_tax_bill is what will be paid NEXT year
        taxes_paid_this_year = taxes_paid_prev_year   # save before updating
        taxes_paid_prev_year = total_tax_bill          # prepare for next year

        # ── 9. Net Worth ────────────────────────────────────────────────────
        liquid_nw = b_taxable + b_pretax_p1 + b_pretax_p2 + b_roth_p1 + b_roth_p2

        primary_mortgage_balance = primary_mortgage.principal_remaining if primary_mortgage else 0.0
        rental_mortgage_balance  = sum(m.principal_remaining for m in rental_mortgages.values())

        net_worth = (liquid_nw
                     + primary_home_value
                     + current_rental_value_total
                     - remaining_debt
                     - primary_mortgage_balance
                     - rental_mortgage_balance)

        # ── 10. Record ──────────────────────────────────────────────────────
        records.append({
            'Year':               year,
            'P1_Age':             p1_age,
            'P2_Age':             p2_age,
            'Employment_P1':      round(emp_p1),
            'Employment_P2':      round(emp_p2),
            'Business_Income':    round(business_income_this_year),
            'Passive_Income':     round(passive_income_this_year),
            'SS_P1':              round(ss_p1),
            'SS_P2':              round(ss_p2),
            'Pension_P1':         round(pens_p1),
            'Pension_P2':         round(pens_p2),
            'RMD_P1':             round(rmd_p1),
            'RMD_P2':             round(rmd_p2),
            'Rental_Income':      round(current_rental_income),
            'Total_Income':       round(total_income),
            'Spend_Goal':         round(spend_goal),
            'Medical_Expenses':   round(medical_expenses_this_year),
            'Child_Expenses':     round(child_expenses_this_year),
            'College_Expenses':   round(college_expenses_this_year),
            'One_Time_Expenses':  round(one_time_this_year),
            'Debt_Payment':       round(total_debt_payment),
            'Remaining_Debt':     round(remaining_debt),
            'Rent_Payment':       round(rent_this_year),
            'Insurance_Premium':  round(insurance_premium_this_year),
            'Mortgage_Payment':   round(total_mortgage_payment),
            'Primary_Mortgage_Balance': round(primary_mortgage_balance),
            'Rental_Mortgage_Balance':  round(rental_mortgage_balance),
            'Previous_Taxes':     round(taxes_paid_this_year),   # paid THIS year
            'Cash_Need':          round(cash_need),
            'WD_PreTax_P1':       round(wd_pretax_p1),
            'WD_PreTax_P2':       round(wd_pretax_p2),
            'WD_Taxable':         round(wd_taxable),
            'WD_Roth_P1':         round(wd_roth_p1),
            'WD_Roth_P2':         round(wd_roth_p2),
            'Roth_Conversion':    round(roth_conversion),
            'Conv_P1':            round(conv_p1),
            'Conv_P2':            round(conv_p2),
            'Contrib_P1_401k':    round(contrib_p1_401k),
            'Contrib_P2_401k':    round(contrib_p2_401k),
            'Match_P1':           round(match_p1),
            'Match_P2':           round(match_p2),
            'Contrib_Strategy':   contrib_strategy_used,
            'Ord_Income':         round(final_ord_income),
            'Taxable_SS':         round(taxable_ss),
            'Cap_Gains':          round(capital_gains),
            'Federal_Tax':        round(federal_tax),
            'FICA_Tax':           round(fica_tax),
            'State_Tax':          round(state_tax),
            'Tax_Bill':           round(total_tax_bill),
            'Taxes_Paid':         round(taxes_paid_this_year),   # same as Previous_Taxes
            'Bal_PreTax_P1':      round(b_pretax_p1),
            'Bal_PreTax_P2':      round(b_pretax_p2),
            'Bal_Roth_P1':        round(b_roth_p1),
            'Bal_Roth_P2':        round(b_roth_p2),
            'Bal_Taxable':        round(b_taxable),
            'Primary_Home':       round(primary_home_value),
            'Rental_Assets':      round(current_rental_value_total),
            'Liquid_Net_Worth':   round(liquid_nw),
            'Net_Worth':          round(net_worth),
            'Market_Return':      round((g_taxable + market_adj) * 100, 2),
        })

        # ── 11. Advance state for next year ─────────────────────────────────
        p1_age += 1
        p2_age += 1
        inflation_idx *= (1 + inflation_rate)

        # Grow salaries (separate from inflation for more accuracy)
        if p1_age <= p1_retire_age:
            p1_salary_current *= (1 + p1_salary_growth)
        if p2_age <= config['p2_employment_until_age']:
            p2_salary_current *= (1 + p2_salary_growth)

        # Grow passive income
        passive_income_current *= (1 + passive_income_growth_rate)

    return records
