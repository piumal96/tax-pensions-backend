import numpy as np
from engine.real_estate import Mortgage
from engine.taxes import TaxCalculator
from engine.withdrawals import StandardStrategy, TaxableFirstStrategy

class SimulationConfig:
    """
    Pure Python Object to hold simulation configuration.
    No validation logic here (that's schemas layer).
    Just data storage.
    """
    def __init__(self, start_year=2025, **kwargs):
        self.start_year = start_year
        self.inputs = kwargs

    def get(self, key, default=0):
        return self.inputs.get(key, default)

    def __getitem__(self, key):
        return self.inputs[key]


def get_rmd_factor(age, rmd_table):
    """Get RMD divisor for age."""
    if age < 73:
        return 0
    if age >= 120:
        return 2.0
    return rmd_table.get(age, 27.4 - (age - 72))


def initialize_mortgages(config):
    """Initialize mortgages based on config."""
    primary = None
    rentals = {}
    
    # Primary Home Mortgage
    primary_principal = config.get('primary_home_mortgage_principal', 0)
    primary_rate = config.get('primary_home_mortgage_rate', 0)
    if 'primary_home_mortgage_rate' in config.inputs and config.get('primary_home_mortgage_rate') > 1:
         # Handle percentage input from CSV if legacy
         primary_rate = primary_rate / 100
         
    primary_years = config.get('primary_home_mortgage_years', 0)
    
    if primary_principal > 0 and primary_years > 0:
        primary = Mortgage(primary_principal, primary_rate, primary_years)
    
    # Rental Property Mortgages
    i = 1
    while True:
        rental_principal_key = f'rental_{i}_mortgage_principal'
        if rental_principal_key not in config.inputs:
            break
        
        rental_principal = config.get(rental_principal_key, 0)
        rental_rate_key = f'rental_{i}_mortgage_rate'
        rental_rate = config.get(rental_rate_key, 0)
        if rental_rate_key in config.inputs and rental_rate > 1:
            rental_rate = rental_rate / 100 # Handle percentage input
            
        rental_years = config.get(f'rental_{i}_mortgage_years', 0)
        
        if rental_principal > 0 and rental_years > 0:
            rentals[i] = Mortgage(rental_principal, rental_rate, rental_years)
        
        i += 1
        
    return primary, rentals


def run_deterministic(config: SimulationConfig, strategy_name: str = 'standard', volatility: float = 0.0):
    """
    Run deterministic simulation (core engine logic).
    
    Args:
        config: SimulationConfig object containing all inputs
        strategy_name: 'standard' or 'taxable_first'
        volatility: Market volatility (std dev) for Monte Carlo support. 0.0 for deterministic.
    """
    
    # Initialize components
    tax_calc = TaxCalculator()
    
    if strategy_name == 'taxable_first':
        strategy = TaxableFirstStrategy()
    else:
        strategy = StandardStrategy()
        
    # RMD Table (Uniform Lifetime)
    rmd_table = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1,
        80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2,
        87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1,
        94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8, 98: 7.3, 99: 6.8, 100: 6.4,
        101: 6.0, 102: 5.6, 103: 5.2, 104: 4.9, 105: 4.6, 106: 4.3, 107: 4.1,
        108: 3.9, 109: 3.7, 110: 3.5, 111: 3.4, 112: 3.3, 113: 3.1, 114: 3.0,
        115: 2.9, 116: 2.8, 117: 2.7, 118: 2.5, 119: 2.3, 120: 2.0
    }
    
    primary_mortgage, rental_mortgages = initialize_mortgages(config)
    
    # Initialize ages
    p1_age = int(config['p1_start_age'])
    p2_age = int(config['p2_start_age'])
    end_age = int(config['end_simulation_age'])
    
    # Initialize account balances
    b_taxable = config['bal_taxable']
    b_pretax_p1 = config['bal_pretax_p1']
    b_pretax_p2 = config['bal_pretax_p2']
    b_roth_p1 = config['bal_roth_p1']
    b_roth_p2 = config['bal_roth_p2']
    
    # Real Estate Assets
    primary_home_value = config.get('primary_home_value', 0)
    primary_home_growth_rate = config.get('primary_home_growth_rate', config.get('inflation_rate', 0.025))
    
    # Parse Rental Properties
    rental_assets = []
    i = 1
    while True:
        r_val_key = f'rental_{i}_value'
        if r_val_key in config.inputs:
            rental_assets.append({
                'id': i,
                'value': config.inputs[r_val_key],
                'income': config.get(f'rental_{i}_income', 0),
                'growth_rate': config.get(f'rental_{i}_growth_rate', config.get('inflation_rate', 0.025)),
                'income_growth_rate': config.get(f'rental_{i}_income_growth_rate', config.get('inflation_rate', 0.025))
            })
            i += 1
        else:
            break
            
    inflation_idx = 1.0
    previous_year_taxes = config.get('previous_year_taxes', 0)
    
    records = []
    year = config.start_year
    
    # --- SIMULATION LOOP ---
    while p1_age <= end_age:
        year += 1
        
        # --- 1. Account Growth ---
        market_adj = 0.0
        if volatility > 0:
            market_adj = np.random.normal(0, volatility)
        
        # Calculate actual market return for this year (base + volatility adjustment)
        actual_market_return = config['growth_rate_taxable'] + market_adj
            
        b_taxable *= (1 + config['growth_rate_taxable'] + market_adj)
        b_pretax_p1 *= (1 + config['growth_rate_pretax_p1'] + market_adj)
        b_pretax_p2 *= (1 + config['growth_rate_pretax_p2'] + market_adj)
        b_roth_p1 *= (1 + config['growth_rate_roth_p1'] + market_adj)
        b_roth_p2 *= (1 + config['growth_rate_roth_p2'] + market_adj)
        
        # Primary Home Growth
        primary_home_value *= (1 + primary_home_growth_rate)
        
        # Rental Properties Growth
        current_rental_income = 0
        current_rental_value_total = 0
        
        for rental in rental_assets:
            # Grow value
            rental['value'] *= (1 + rental['growth_rate'])
            current_rental_value_total += rental['value']
            
            # Determine Rental Income
            this_year_income = rental['income']
            if this_year_income == 0:
                # Default calculation: (Value / 500k) * 2000 * 12
                # This logic matches original RetirementSimulator
                if rental['value'] > 0:
                     monthly_rent = (rental['value'] / 500000) * 2000
                     this_year_income = monthly_rent * 12
            else:
                # Grow existing income
                rental['income'] *= (1 + rental['income_growth_rate'])
                this_year_income = rental['income']
                
            current_rental_income += this_year_income
            
        # --- 2. Income Sources ---
        emp_p1 = 0
        if p1_age < config['p1_employment_until_age']:
            emp_p1 = config['p1_employment_income'] * inflation_idx
        
        emp_p2 = 0
        if p2_age < config['p2_employment_until_age']:
            emp_p2 = config['p2_employment_income'] * inflation_idx
            
        ss_p1 = 0
        if p1_age >= config['p1_ss_start_age']:
            ss_p1 = config['p1_ss_amount'] * inflation_idx
        
        ss_p2 = 0
        if p2_age >= config['p2_ss_start_age']:
            ss_p2 = config['p2_ss_amount'] * inflation_idx
            
        ss_total = ss_p1 + ss_p2
        
        pens_p1 = 0
        if p1_age >= config['p1_pension_start_age']:
            pens_p1 = config['p1_pension'] * inflation_idx
        
        pens_p2 = 0
        if p2_age >= config['p2_pension_start_age']:
            pens_p2 = config['p2_pension'] * inflation_idx
            
        pens_total = pens_p1 + pens_p2
        
        # RMD Calculations
        rmd_p1 = 0
        if p1_age >= 73 and b_pretax_p1 > 0:
            factor = get_rmd_factor(p1_age, rmd_table)
            if factor > 0:
                rmd_p1 = b_pretax_p1 / factor
        
        rmd_p2 = 0
        if p2_age >= 73 and b_pretax_p2 > 0:
            factor = get_rmd_factor(p2_age, rmd_table)
            if factor > 0:
                rmd_p2 = b_pretax_p2 / factor
                
        rmd_total = rmd_p1 + rmd_p2
        
        # --- 3a. Mortgages ---
        total_mortgage_payment = 0
        # Tracks not used in strategy but good for output if needed
        
        if primary_mortgage and not primary_mortgage.is_paid_off():
            primary_mortgage.make_payment(12)
            total_mortgage_payment += primary_mortgage.get_annual_payment()
            
        for rid, m in rental_mortgages.items():
            if not m.is_paid_off():
                m.make_payment(12)
                total_mortgage_payment += m.get_annual_payment()
                
        # --- 3b. Cash Need ---
        spend_goal = config['annual_spend_goal'] * inflation_idx
        cash_need = spend_goal + total_mortgage_payment + previous_year_taxes
        
        # --- 4. Withdrawals ---
        strategy_inputs = {
            'p1_age': p1_age,
            'p2_age': p2_age,
            'spend_goal': spend_goal,
            'previous_year_taxes': previous_year_taxes,
            'target_tax_bracket_rate': config['target_tax_bracket_rate']
        }
        
        account_balances = (b_taxable, b_pretax_p1, b_pretax_p2, b_roth_p1, b_roth_p2)
        income_sources = (emp_p1, emp_p2, ss_total, pens_total, rmd_p1, rmd_p2)
        
        s_res = strategy.execute(
            strategy_inputs,
            account_balances,
            income_sources,
            inflation_idx,
            rmd_table,
            tax_calc.brackets_ordinary,
            tax_calc.std_deduction
        )
        
        wd_pretax_p1 = s_res['wd_pretax_p1']
        wd_pretax_p2 = s_res['wd_pretax_p2']
        wd_taxable = s_res['wd_taxable']
        wd_roth_p1 = s_res['wd_roth_p1']
        wd_roth_p2 = s_res['wd_roth_p2']
        roth_conversion = s_res['roth_conversion']
        conv_p1 = s_res['conv_p1']
        conv_p2 = s_res['conv_p2']
        
        total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total + current_rental_income
        
        # --- 5. Update Balances ---
        b_pretax_p1 -= (rmd_p1 + wd_pretax_p1 + conv_p1)
        b_pretax_p2 -= (rmd_p2 + wd_pretax_p2 + conv_p2)
        b_roth_p1 += conv_p1
        b_roth_p1 -= wd_roth_p1
        b_roth_p2 += conv_p2
        b_roth_p2 -= wd_roth_p2
        b_taxable -= wd_taxable
        
        # --- 6. Taxes ---
        final_ord_income = (emp_p1 + emp_p2 + ss_total + pens_total + 
                           rmd_total + wd_pretax_p1 + wd_pretax_p2 + roth_conversion + current_rental_income)
                           
        basis_ratio = config['taxable_basis_ratio']
        capital_gains = wd_taxable * (1 - basis_ratio)
        
        tax_bill = tax_calc.calculate_tax(final_ord_income, capital_gains, inflation_idx)
        previous_year_taxes = tax_bill  # For next year
        
        # --- 7. Record ---
        liquid_net_worth = b_taxable + b_pretax_p1 + b_pretax_p2 + b_roth_p1 + b_roth_p2
        net_worth = liquid_net_worth + primary_home_value + current_rental_value_total
        
        records.append({
            'Year': year,
            'P1_Age': p1_age,
            'P2_Age': p2_age,
            'Employment_P1': round(emp_p1),
            'Employment_P2': round(emp_p2),
            'SS_P1': round(ss_p1),
            'SS_P2': round(ss_p2),
            'Pension_P1': round(pens_p1),
            'Pension_P2': round(pens_p2),
            'RMD_P1': round(rmd_p1),
            'RMD_P2': round(rmd_p2),
            'Rental_Income': round(current_rental_income),
            'Total_Income': round(total_income),
            'Spend_Goal': round(spend_goal),
            'Previous_Taxes': round(previous_year_taxes),
            'Cash_Need': round(cash_need),
            'WD_PreTax_P1': round(wd_pretax_p1),
            'WD_PreTax_P2': round(wd_pretax_p2),
            'WD_Taxable': round(wd_taxable),
            'WD_Roth_P1': round(wd_roth_p1),
            'WD_Roth_P2': round(wd_roth_p2),
            'Roth_Conversion': round(roth_conversion),
            'Conv_P1': round(conv_p1),
            'Conv_P2': round(conv_p2),
            'Ord_Income': round(final_ord_income),
            'Cap_Gains': round(capital_gains),
            'Tax_Bill': round(tax_bill),
            'Taxes_Paid': 0, # Paid next year
            'Bal_PreTax_P1': round(b_pretax_p1),
            'Bal_PreTax_P2': round(b_pretax_p2),
            'Bal_Roth_P1': round(b_roth_p1),
            'Bal_Roth_P2': round(b_roth_p2),
            'Bal_Taxable': round(b_taxable),
            'Primary_Home': round(primary_home_value),
            'Rental_Assets': round(current_rental_value_total),
            'Net_Worth': round(net_worth),
            'Market_Return': round(actual_market_return * 100, 2)  # Store as percentage (e.g., 7.5 for 7.5%)
        })
        
        # Advance ages
        p1_age += 1
        p2_age += 1
        inflation_idx *= (1 + config['inflation_rate'])
        
    return records
