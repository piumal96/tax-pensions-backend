import pandas as pd
import numpy as np
import sys
import os
from abc import ABC, abstractmethod


class Mortgage:
    """
    Manages mortgage calculations and amortization tracking.
    Supports mortgages on primary home and rental properties.
    """
    
    def __init__(self, principal_remaining, annual_interest_rate, years_remaining):
        """
        Initialize mortgage.
        
        Args:
            principal_remaining: Current principal balance
            annual_interest_rate: Annual interest rate (e.g., 0.065 for 6.5%)
            years_remaining: Years left on the mortgage
        """
        self.principal_remaining = max(0, principal_remaining)
        self.annual_interest_rate = max(0, annual_interest_rate)
        self.years_remaining = max(0, years_remaining)
        self.original_principal = self.principal_remaining
        self.months_remaining = int(self.years_remaining * 12)
        self.monthly_payment = 0
        self.interest_paid_this_year = 0
        self.principal_paid_this_year = 0
        
        self._calculate_monthly_payment()
    
    def _calculate_monthly_payment(self):
        """Calculate monthly mortgage payment using standard formula."""
        if self.principal_remaining <= 0 or self.months_remaining <= 0:
            self.monthly_payment = 0
            return
        
        monthly_rate = self.annual_interest_rate / 12
        
        if monthly_rate == 0:
            # No interest rate - just divide principal by remaining months
            self.monthly_payment = self.principal_remaining / self.months_remaining
        else:
            # Standard mortgage payment formula: P = L[c(1+c)^n]/[(1+c)^n-1]
            numerator = monthly_rate * ((1 + monthly_rate) ** self.months_remaining)
            denominator = ((1 + monthly_rate) ** self.months_remaining) - 1
            self.monthly_payment = self.principal_remaining * (numerator / denominator)
    
    def get_annual_payment(self):
        """Get total annual mortgage payment."""
        return self.monthly_payment * 12
    
    def make_payment(self, num_months=12):
        """
        Process mortgage payments for specified months.
        Updates principal, tracks interest and principal paid.
        
        Args:
            num_months: Number of months to process (default 12 for annual)
        """
        self.interest_paid_this_year = 0
        self.principal_paid_this_year = 0
        
        for _ in range(num_months):
            if self.principal_remaining <= 0 or self.monthly_payment <= 0:
                break
            
            monthly_rate = self.annual_interest_rate / 12
            interest_payment = self.principal_remaining * monthly_rate
            principal_payment = self.monthly_payment - interest_payment
            
            # Ensure we don't overpay principal
            if principal_payment > self.principal_remaining:
                principal_payment = self.principal_remaining
                interest_payment = self.monthly_payment - principal_payment
            
            self.principal_remaining -= principal_payment
            self.interest_paid_this_year += interest_payment
            self.principal_paid_this_year += principal_payment
            
            self.principal_remaining = max(0, self.principal_remaining)
        
        # Recalculate months remaining and payment
        if self.principal_remaining > 0:
            self.months_remaining = max(0, self.months_remaining - num_months)
            self.years_remaining = self.months_remaining / 12
            if self.months_remaining > 0 and self.annual_interest_rate > 0:
                self._calculate_monthly_payment()
        else:
            self.months_remaining = 0
            self.years_remaining = 0
            self.monthly_payment = 0
    
    def is_paid_off(self):
        """Check if mortgage is fully paid."""
        return self.principal_remaining <= 0
    
    def get_status(self):
        """Get current mortgage status as dict."""
        return {
            'principal_remaining': self.principal_remaining,
            'interest_paid_this_year': self.interest_paid_this_year,
            'principal_paid_this_year': self.principal_paid_this_year,
            'annual_payment': self.get_annual_payment(),
            'years_remaining': max(0, self.years_remaining),
            'paid_off': self.is_paid_off()
        }


class WithdrawalStrategy(ABC):
    """Abstract base class for withdrawal strategies"""
    
    @abstractmethod
    def execute(self, inputs, account_balances, income_sources, inflation_idx, rmd_table, brackets_ordinary, std_deduction):
        """
        Execute the withdrawal strategy.
        
        Returns:
            dict with withdrawal amounts and conversions
        """
        pass


class StandardStrategy(WithdrawalStrategy):
    """
    Current standard strategy:
    1. Employment, SS, Pensions, RMDs (forced)
    2. Voluntary pretax withdrawals (older first) 
    3. Taxable
    4. Roth
    5. Fill bracket with Roth conversions
    """
    
    def execute(self, inputs, account_balances, income_sources, inflation_idx, rmd_table, brackets_ordinary, std_deduction):
        """Execute standard withdrawal strategy."""
        
        b_taxable, b_pretax_p1, b_pretax_p2, b_roth_p1, b_roth_p2 = account_balances
        emp_p1, emp_p2, ss_total, pens_total, rmd_p1, rmd_p2 = income_sources
        p1_age, p2_age = inputs['p1_age'], inputs['p2_age']
        
        rmd_total = rmd_p1 + rmd_p2
        total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total
        spend_goal = inputs['spend_goal']
        previous_year_taxes = inputs['previous_year_taxes']
        cash_need = spend_goal + previous_year_taxes
        
        wd_pretax_p1 = 0
        wd_pretax_p2 = 0
        wd_roth_p1 = 0
        wd_roth_p2 = 0
        wd_taxable = 0
        conv_p1 = 0
        conv_p2 = 0
        roth_conversion = 0
        
        # Shortfall after income, RMDs
        shortfall = cash_need - total_income
        
        if shortfall > 0:
            # Take from pretax - older person first
            if p1_age >= p2_age:
                take_p1 = min(shortfall, max(0, b_pretax_p1 - rmd_p1))
                wd_pretax_p1 = take_p1
                shortfall -= take_p1
                
                if shortfall > 0:
                    take_p2 = min(shortfall, max(0, b_pretax_p2 - rmd_p2))
                    wd_pretax_p2 = take_p2
                    shortfall -= take_p2
            else:
                take_p2 = min(shortfall, max(0, b_pretax_p2 - rmd_p2))
                wd_pretax_p2 = take_p2
                shortfall -= take_p2
                
                if shortfall > 0:
                    take_p1 = min(shortfall, max(0, b_pretax_p1 - rmd_p1))
                    wd_pretax_p1 = take_p1
                    shortfall -= take_p1
            
            # Take from taxable
            if shortfall > 0:
                wd_taxable = min(shortfall, b_taxable)
                shortfall -= wd_taxable
            
            # Take from Roth (P1 first, then P2)
            if shortfall > 0:
                take_r1 = min(shortfall, b_roth_p1)
                wd_roth_p1 = take_r1
                shortfall -= take_r1
                
                if shortfall > 0:
                    take_r2 = min(shortfall, b_roth_p2)
                    wd_roth_p2 = take_r2
                    shortfall -= take_r2
        
        # Roth conversion - fill the bracket
        current_ord_income = (emp_p1 + emp_p2 + ss_total + pens_total + 
                             rmd_total + wd_pretax_p1 + wd_pretax_p2)
        
        bracket_room = self._get_bracket_room(current_ord_income, inflation_idx, 
                                              inputs['target_tax_bracket_rate'], 
                                              brackets_ordinary, std_deduction)
        
        pretax_left_p1 = max(0, b_pretax_p1 - rmd_p1 - wd_pretax_p1)
        pretax_left_p2 = max(0, b_pretax_p2 - rmd_p2 - wd_pretax_p2)
        pretax_left_total = pretax_left_p1 + pretax_left_p2
        
        if bracket_room > 0 and pretax_left_total > 0:
            conversion_amount = min(bracket_room, pretax_left_total)
            
            if p1_age >= p2_age:
                conv_p1 = min(conversion_amount, pretax_left_p1)
                conversion_amount -= conv_p1
                conv_p2 = min(conversion_amount, pretax_left_p2)
                roth_conversion = conv_p1 + conv_p2
            else:
                conv_p2 = min(conversion_amount, pretax_left_p2)
                conversion_amount -= conv_p2
                conv_p1 = min(conversion_amount, pretax_left_p1)
                roth_conversion = conv_p1 + conv_p2
        
        return {
            'wd_pretax_p1': wd_pretax_p1,
            'wd_pretax_p2': wd_pretax_p2,
            'wd_taxable': wd_taxable,
            'wd_roth_p1': wd_roth_p1,
            'wd_roth_p2': wd_roth_p2,
            'roth_conversion': roth_conversion,
            'conv_p1': conv_p1,
            'conv_p2': conv_p2
        }
    
    def _get_bracket_room(self, current_ord_income, inflation_idx, target_rate, brackets_ordinary, std_deduction):
        """How much room is left in the target tax bracket?"""
        adj_std_ded = std_deduction * inflation_idx
        taxable_income = max(0, current_ord_income - adj_std_ded)
        
        adj_brackets = [(lim * inflation_idx, rate) for lim, rate in brackets_ordinary]
        
        target_limit = 0
        for limit, rate in adj_brackets:
            if rate == target_rate:
                target_limit = limit
                break
        
        if target_limit == 0:
            return 0
        
        room = max(0, target_limit - taxable_income)
        return room


class TaxableFirstStrategy(WithdrawalStrategy):
    """
    New taxable-first strategy:
    1. Use taxable for taxes/expenses first
    2. Use RMDs when they start
    3. Fill up to target tax bracket with other income
    4. Perform Roth conversions with remaining pretax
    
    This allows more Roth conversions since taxes are paid by taxable pool.
    """
    
    def execute(self, inputs, account_balances, income_sources, inflation_idx, rmd_table, brackets_ordinary, std_deduction):
        """Execute taxable-first withdrawal strategy."""
        
        b_taxable, b_pretax_p1, b_pretax_p2, b_roth_p1, b_roth_p2 = account_balances
        emp_p1, emp_p2, ss_total, pens_total, rmd_p1, rmd_p2 = income_sources
        p1_age, p2_age = inputs['p1_age'], inputs['p2_age']
        
        rmd_total = rmd_p1 + rmd_p2
        total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total
        spend_goal = inputs['spend_goal']
        previous_year_taxes = inputs['previous_year_taxes']
        cash_need = spend_goal + previous_year_taxes
        
        wd_pretax_p1 = 0
        wd_pretax_p2 = 0
        wd_roth_p1 = 0
        wd_roth_p2 = 0
        wd_taxable = 0
        conv_p1 = 0
        conv_p2 = 0
        roth_conversion = 0
        
        # Step 1: Use RMDs (they're mandatory)
        wd_from_rmd = rmd_total
        
        # Step 2: Exhaust taxable first for remaining cash needs
        remaining_need = max(0, cash_need - total_income)
        
        if remaining_need > 0:
            wd_taxable = min(remaining_need, b_taxable)
            remaining_need -= wd_taxable
        
        # Step 3: If still need cash, take from Roth (tax-free)
        if remaining_need > 0:
            take_r1 = min(remaining_need, b_roth_p1)
            wd_roth_p1 = take_r1
            remaining_need -= take_r1
            
            if remaining_need > 0:
                take_r2 = min(remaining_need, b_roth_p2)
                wd_roth_p2 = take_r2
                remaining_need -= take_r2
        
        # Step 4: If still need, take from pretax but leave room for conversions
        if remaining_need > 0:
            if p1_age >= p2_age:
                take_p1 = min(remaining_need, max(0, b_pretax_p1 - rmd_p1))
                wd_pretax_p1 = take_p1
                remaining_need -= take_p1
                
                if remaining_need > 0:
                    take_p2 = min(remaining_need, max(0, b_pretax_p2 - rmd_p2))
                    wd_pretax_p2 = take_p2
                    remaining_need -= take_p2
            else:
                take_p2 = min(remaining_need, max(0, b_pretax_p2 - rmd_p2))
                wd_pretax_p2 = take_p2
                remaining_need -= take_p2
                
                if remaining_need > 0:
                    take_p1 = min(remaining_need, max(0, b_pretax_p1 - rmd_p1))
                    wd_pretax_p1 = take_p1
                    remaining_need -= take_p1
        
        # Step 5: Calculate current ordinary income (excluding conversions yet)
        current_ord_income = (emp_p1 + emp_p2 + ss_total + pens_total + 
                             rmd_total + wd_pretax_p1 + wd_pretax_p2)
        
        # Step 6: Roth conversions - fill up to target bracket
        bracket_room = self._get_bracket_room(current_ord_income, inflation_idx, 
                                              inputs['target_tax_bracket_rate'], 
                                              brackets_ordinary, std_deduction)
        
        # How much pretax is available for conversion?
        pretax_left_p1 = max(0, b_pretax_p1 - rmd_p1 - wd_pretax_p1)
        pretax_left_p2 = max(0, b_pretax_p2 - rmd_p2 - wd_pretax_p2)
        pretax_left_total = pretax_left_p1 + pretax_left_p2
        
        if bracket_room > 0 and pretax_left_total > 0:
            conversion_amount = min(bracket_room, pretax_left_total)
            
            if p1_age >= p2_age:
                conv_p1 = min(conversion_amount, pretax_left_p1)
                conversion_amount -= conv_p1
                conv_p2 = min(conversion_amount, pretax_left_p2)
                roth_conversion = conv_p1 + conv_p2
            else:
                conv_p2 = min(conversion_amount, pretax_left_p2)
                conversion_amount -= conv_p2
                conv_p1 = min(conversion_amount, pretax_left_p1)
                roth_conversion = conv_p1 + conv_p2
        
        return {
            'wd_pretax_p1': wd_pretax_p1,
            'wd_pretax_p2': wd_pretax_p2,
            'wd_taxable': wd_taxable,
            'wd_roth_p1': wd_roth_p1,
            'wd_roth_p2': wd_roth_p2,
            'roth_conversion': roth_conversion,
            'conv_p1': conv_p1,
            'conv_p2': conv_p2
        }
    
    def _get_bracket_room(self, current_ord_income, inflation_idx, target_rate, brackets_ordinary, std_deduction):
        """How much room is left in the target tax bracket?"""
        adj_std_ded = std_deduction * inflation_idx
        taxable_income = max(0, current_ord_income - adj_std_ded)
        
        adj_brackets = [(lim * inflation_idx, rate) for lim, rate in brackets_ordinary]
        
        target_limit = 0
        for limit, rate in adj_brackets:
            if rate == target_rate:
                target_limit = limit
                break
        
        if target_limit == 0:
            return 0
        
        room = max(0, target_limit - taxable_income)
        return room


class RetirementSimulator:
    """
    Simplified retirement simulator with:
    - Individual pretax and roth accounts per person (p1, p2)
    - Joint taxable account
    - Individual employment income until stated age
    - Previous year tax tracking
    - Pluggable withdrawal strategy with roth conversions
    """
    
    def __init__(self, config_file='nisha.csv', year=2025, strategy='standard'):
        self.year = year
        self.config_name = os.path.splitext(os.path.basename(config_file))[0]
        
        # Set withdrawal strategy
        if strategy == 'taxable_first':
            self.strategy = TaxableFirstStrategy()
        else:
            self.strategy = StandardStrategy()
        
        try:
            df_config = pd.read_csv(config_file)
            self.inputs = dict(zip(df_config['parameter'], df_config['value']))
        except FileNotFoundError:
            print(f"Error: {config_file} not found.")
            sys.exit(1)
        
        # Parse numeric inputs
        for k, v in self.inputs.items():
            try:
                self.inputs[k] = float(v)
            except ValueError:
                pass
        
        # 2024 Tax Brackets (MFJ)
        self.brackets_ordinary = [
            (24800, 0.10), (100800, 0.12), (211400, 0.22),
            (403550, 0.24), (512450, 0.32), (768700, 0.35), (10000000, 0.37)
        ]
        
        # Long-term capital gains brackets (MFJ)
        self.brackets_ltcg = [
            (96700, 0.00), (600050, 0.15), (10000000, 0.20)
        ]
        
        self.std_deduction = 32200
        
        # RMD Table (Uniform Lifetime)
        self.rmd_table = {
            73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1,
            80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2,
            87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1,
            94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8, 98: 7.3, 99: 6.8, 100: 6.4,
            101: 6.0, 102: 5.6, 103: 5.2, 104: 4.9, 105: 4.6, 106: 4.3, 107: 4.1,
            108: 3.9, 109: 3.7, 110: 3.5, 111: 3.4, 112: 3.3, 113: 3.1, 114: 3.0,
            115: 2.9, 116: 2.8, 117: 2.7, 118: 2.5, 119: 2.3, 120: 2.0
        }
        
        # Initialize mortgages - will be created during simulation
        self.primary_home_mortgage = None
        self.rental_mortgages = {}
        self._initialize_mortgages()

    def get_rmd_factor(self, age):
        """Get RMD divisor for age."""
        if age < 73:
            return 0
        if age >= 120:
            return 2.0
        return self.rmd_table.get(age, 27.4 - (age - 72))

    def _initialize_mortgages(self):
        """Initialize mortgages for primary home and rental properties."""
        # Primary Home Mortgage
        primary_principal = self.inputs.get('primary_home_mortgage_principal', 0)
        primary_rate = self.inputs.get('primary_home_mortgage_rate', 0) / 100 if 'primary_home_mortgage_rate' in self.inputs else 0
        primary_years = self.inputs.get('primary_home_mortgage_years', 0)
        
        if primary_principal > 0 and primary_years > 0:
            self.primary_home_mortgage = Mortgage(primary_principal, primary_rate, primary_years)
        
        # Rental Property Mortgages
        i = 1
        while True:
            rental_principal_key = f'rental_{i}_mortgage_principal'
            if rental_principal_key not in self.inputs:
                break
            
            rental_principal = self.inputs.get(rental_principal_key, 0)
            rental_rate = self.inputs.get(f'rental_{i}_mortgage_rate', 0) / 100 if f'rental_{i}_mortgage_rate' in self.inputs else 0
            rental_years = self.inputs.get(f'rental_{i}_mortgage_years', 0)
            
            if rental_principal > 0 and rental_years > 0:
                self.rental_mortgages[i] = Mortgage(rental_principal, rental_rate, rental_years)
            
            i += 1


    def calculate_tax(self, ordinary_income, capital_gains, inflation_factor):
        """
        Calculate federal tax by stacking capital gains on top of ordinary income.
        Uses 2024 brackets adjusted for inflation.
        """
        if ordinary_income + capital_gains <= 0:
            return 0
        
        # Adjust brackets for inflation
        adj_std_ded = self.std_deduction * inflation_factor
        adj_brackets_ord = [(lim * inflation_factor, rate) for lim, rate in self.brackets_ordinary]
        adj_brackets_ltcg = [(lim * inflation_factor, rate) for lim, rate in self.brackets_ltcg]
        
        # Taxable ordinary income after standard deduction
        taxable_ord = max(0, ordinary_income - adj_std_ded)
        
        # Calculate ordinary income tax
        ord_tax = 0
        prev_limit = 0
        for limit, rate in adj_brackets_ord:
            if taxable_ord > prev_limit:
                taxable_in_bracket = min(taxable_ord, limit) - prev_limit
                ord_tax += taxable_in_bracket * rate
                prev_limit = limit
            else:
                break
        
        # Calculate capital gains tax (stacked on top)
        ltcg_tax = 0
        ltcg_floor = taxable_ord
        ltcg_ceiling = taxable_ord + capital_gains
        
        for limit, rate in adj_brackets_ltcg:
            if ltcg_ceiling > ltcg_floor and ltcg_floor < limit:
                fill = min(ltcg_ceiling, limit) - ltcg_floor
                ltcg_tax += fill * rate
                ltcg_floor = min(ltcg_ceiling, limit)
                if ltcg_floor >= ltcg_ceiling:
                    break
        
        return ord_tax + ltcg_tax

    def run(self, verbose=False, volatility=0.0):
        """
        Run the retirement simulation.
        
        Args:
            verbose (bool): Print debug info.
            volatility (float): Standard deviation for annual investment returns.
                                e.g., 0.15 for 15% volatility.
        """
        
        # Initialize ages
        p1_age = int(self.inputs['p1_start_age'])
        p2_age = int(self.inputs['p2_start_age'])
        end_age = int(self.inputs['end_simulation_age'])
        
        # Initialize account balances
        b_taxable = self.inputs['bal_taxable']
        b_pretax_p1 = self.inputs['bal_pretax_p1']
        b_pretax_p2 = self.inputs['bal_pretax_p2']
        b_roth_p1 = self.inputs['bal_roth_p1']
        b_roth_p2 = self.inputs['bal_roth_p2']
        
        # Real Estate Assets
        primary_home_value = self.inputs.get('primary_home_value', 0)
        primary_home_growth_rate = self.inputs.get('primary_home_growth_rate', self.inputs.get('inflation_rate', 0.025))
        
        # Parse Rental Properties (dynamic keys: rental_1_value, rental_2_value, etc.)
        rental_assets = []
        i = 1
        while True:
            r_val_key = f'rental_{i}_value'
            if r_val_key in self.inputs:
                rental_assets.append({
                    'id': i,
                    'value': self.inputs[r_val_key],
                    'income': self.inputs.get(f'rental_{i}_income', 0),
                    'growth_rate': self.inputs.get(f'rental_{i}_growth_rate', self.inputs.get('inflation_rate', 0.025)),
                    'income_growth_rate': self.inputs.get(f'rental_{i}_income_growth_rate', self.inputs.get('inflation_rate', 0.025))
                })
                i += 1
            else:
                break        
        inflation_idx = 1.0
        previous_year_taxes = self.inputs.get('previous_year_taxes', 0)
        
        records = []
        year = self.year
        
        while p1_age <= end_age:
            year += 1
            
            # --- 1. Account Growth ---
            # Apply volatility (Market Fluctuation)
            # We assume all investment accounts are correlated to the market
            # Generate a single random adjustment for this year
            market_adj = 0.0
            if volatility > 0:
                market_adj = np.random.normal(0, volatility)
                
            b_taxable *= (1 + self.inputs['growth_rate_taxable'] + market_adj)
            b_pretax_p1 *= (1 + self.inputs['growth_rate_pretax_p1'] + market_adj)
            b_pretax_p2 *= (1 + self.inputs['growth_rate_pretax_p2'] + market_adj)
            b_roth_p1 *= (1 + self.inputs['growth_rate_roth_p1'] + market_adj)
            b_roth_p2 *= (1 + self.inputs['growth_rate_roth_p2'] + market_adj)
            
            # Primary Home Growth
            primary_home_value *= (1 + primary_home_growth_rate)
            
            # Rental Properties Growth & Income
            current_rental_income = 0
            current_rental_value_total = 0
            
            for rental in rental_assets:
                # Grow value
                rental['value'] *= (1 + rental['growth_rate'])
                current_rental_value_total += rental['value']
                
                # Determine Rental Income
                # Rule: If explicitly provided > 0, use it.
                # Else, calculate default: $2000 per $500k value * 12 months = 4.8% annual
                
                this_year_income = rental['income']
                if this_year_income == 0:
                    # Default calculation based on CURRENT value
                    # (Value / 500k) * 2000 * 12
                    monthly_rent = (rental['value'] / 500000) * 2000
                    this_year_income = monthly_rent * 12
                else:
                    # Apply growth to existing income
                    rental['income'] *= (1 + rental['income_growth_rate'])
                    this_year_income = rental['income']
                    
                current_rental_income += this_year_income
            
            # --- 2. Income Sources ---
            # Employment Income (each person individually until retirement age)
            emp_p1 = 0
            if p1_age < self.inputs['p1_employment_until_age']:
                emp_p1 = self.inputs['p1_employment_income'] * inflation_idx
            
            emp_p2 = 0
            if p2_age < self.inputs['p2_employment_until_age']:
                emp_p2 = self.inputs['p2_employment_income'] * inflation_idx
            
            # Social Security
            ss_p1 = 0
            if p1_age >= self.inputs['p1_ss_start_age']:
                ss_p1 = self.inputs['p1_ss_amount'] * inflation_idx
            
            ss_p2 = 0
            if p2_age >= self.inputs['p2_ss_start_age']:
                ss_p2 = self.inputs['p2_ss_amount'] * inflation_idx
            
            ss_total = ss_p1 + ss_p2
            
            # Pensions
            pens_p1 = 0
            if p1_age >= self.inputs['p1_pension_start_age']:
                pens_p1 = self.inputs['p1_pension'] * inflation_idx
            
            pens_p2 = 0
            if p2_age >= self.inputs['p2_pension_start_age']:
                pens_p2 = self.inputs['p2_pension'] * inflation_idx
            
            pens_total = pens_p1 + pens_p2
            
            # RMD Calculations
            rmd_p1 = 0
            if p1_age >= 73 and b_pretax_p1 > 0:
                factor = self.get_rmd_factor(p1_age)
                if factor > 0:
                    rmd_p1 = b_pretax_p1 / factor
            
            rmd_p2 = 0
            if p2_age >= 73 and b_pretax_p2 > 0:
                factor = self.get_rmd_factor(p2_age)
                if factor > 0:
                    rmd_p2 = b_pretax_p2 / factor
            
            rmd_total = rmd_p1 + rmd_p2
            
            # Add Rental Income to Total Income logic
            # Rental income is generally taxable ordinary income
            
            # --- 3a. Calculate Mortgage Payments (MANDATORY EXPENSES) ---
            total_mortgage_payment = 0
            mortgage_principal_paid = 0
            mortgage_interest_paid = 0
            
            # Primary Home Mortgage
            primary_mortgage_payment = 0
            primary_mortgage_principal = 0
            primary_mortgage_interest = 0
            
            if self.primary_home_mortgage and not self.primary_home_mortgage.is_paid_off():
                self.primary_home_mortgage.make_payment(12)  # Process annual payment
                primary_mortgage_payment = self.primary_home_mortgage.get_annual_payment()
                primary_mortgage_principal = self.primary_home_mortgage.principal_paid_this_year
                primary_mortgage_interest = self.primary_home_mortgage.interest_paid_this_year
                total_mortgage_payment += primary_mortgage_payment
                mortgage_principal_paid += primary_mortgage_principal
                mortgage_interest_paid += primary_mortgage_interest
            
            # Rental Property Mortgages
            rental_mortgage_payments = {}
            for rental_id, mortgage in self.rental_mortgages.items():
                if not mortgage.is_paid_off():
                    mortgage.make_payment(12)  # Process annual payment
                    rental_pmt = mortgage.get_annual_payment()
                    rental_mortgage_payments[rental_id] = {
                        'payment': rental_pmt,
                        'principal': mortgage.principal_paid_this_year,
                        'interest': mortgage.interest_paid_this_year
                    }
                    total_mortgage_payment += rental_pmt
                    mortgage_principal_paid += mortgage.principal_paid_this_year
                    mortgage_interest_paid += mortgage.interest_paid_this_year
            
            # --- 3b. Calculate Cash Need (includes mortgage as mandatory expense) ---
            # Cash need = spending goal + mortgages + taxes owed from previous year
            spend_goal = self.inputs['annual_spend_goal'] * inflation_idx
            cash_need = spend_goal + total_mortgage_payment + previous_year_taxes
            
            # --- 4. Execute Withdrawal Strategy ---
            strategy_inputs = {
                'p1_age': p1_age,
                'p2_age': p2_age,
                'spend_goal': spend_goal,
                'previous_year_taxes': previous_year_taxes,
                'target_tax_bracket_rate': self.inputs['target_tax_bracket_rate']
            }
            
            account_balances = (b_taxable, b_pretax_p1, b_pretax_p2, b_roth_p1, b_roth_p2)
            income_sources = (emp_p1, emp_p2, ss_total, pens_total, rmd_p1, rmd_p2)
            
            strategy_result = self.strategy.execute(
                strategy_inputs, 
                account_balances, 
                income_sources, 
                inflation_idx, 
                self.rmd_table,
                self.brackets_ordinary,
                self.std_deduction
            )
            
            wd_pretax_p1 = strategy_result['wd_pretax_p1']
            wd_pretax_p2 = strategy_result['wd_pretax_p2']
            wd_taxable = strategy_result['wd_taxable']
            wd_roth_p1 = strategy_result['wd_roth_p1']
            wd_roth_p2 = strategy_result['wd_roth_p2']
            roth_conversion = strategy_result['roth_conversion']
            conv_p1 = strategy_result['conv_p1']
            conv_p2 = strategy_result['conv_p2']
            
            conv_p2 = strategy_result['conv_p2']
            
            total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total + current_rental_income
            
            # --- 5. Update Account Balances ---
            b_pretax_p1 -= (rmd_p1 + wd_pretax_p1 + conv_p1)
            b_pretax_p2 -= (rmd_p2 + wd_pretax_p2 + conv_p2)
            b_roth_p1 += conv_p1
            b_roth_p1 -= wd_roth_p1
            b_roth_p2 += conv_p2
            b_roth_p2 -= wd_roth_p2
            b_taxable -= wd_taxable
            
            # --- 6. Calculate Taxes ---
            # Ordinary income includes employment, SS, pensions, RMDs, pretax withdrawals, conversions, AND RENTAL INCOME
            final_ord_income = (emp_p1 + emp_p2 + ss_total + pens_total + 
                               rmd_total + wd_pretax_p1 + wd_pretax_p2 + roth_conversion + current_rental_income)
            
            # Capital gains from taxable withdrawal
            basis_ratio = self.inputs['taxable_basis_ratio']
            capital_gains = wd_taxable * (1 - basis_ratio)
            
            # Calculate total tax
            tax_bill = self.calculate_tax(final_ord_income, capital_gains, inflation_idx)
            
            # IMPORTANT: Taxes are paid NEXT year, not this year
            # This year's tax_bill is added to next year's cash_need via previous_year_taxes
            # Therefore, do NOT deduct taxes from accounts this year
            taxes_paid = 0
            
            # --- 7. Record Results ---
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
                'Taxes_Paid': round(taxes_paid),
                'Bal_PreTax_P1': round(max(0, b_pretax_p1)),
                'Bal_PreTax_P2': round(max(0, b_pretax_p2)),
                'Bal_Roth_P1': round(max(0, b_roth_p1)),
                'Bal_Roth_P2': round(max(0, b_roth_p2)),
                'Bal_Taxable': round(max(0, b_taxable)),
                'Primary_Home': round(primary_home_value),
                'Rental_Assets': round(current_rental_value_total),
                'Net_Worth': round(max(0, net_worth)),
                'Market_Return': self.inputs['growth_rate_taxable'] + market_adj,
                # Mortgage tracking
                'Mortgage_Payment': round(total_mortgage_payment),
                'Mortgage_Principal': round(mortgage_principal_paid),
                'Mortgage_Interest': round(mortgage_interest_paid),
                'Primary_Mortgage_Principal': round(self.primary_home_mortgage.principal_remaining if self.primary_home_mortgage else 0),
                'Primary_Mortgage_Payment': round(primary_mortgage_payment),
                'Discretionary_Spend': round(spend_goal),
                # Home Equity tracking
                'Primary_Home_Value': round(primary_home_value),
                'Primary_Mortgage_Liability': round(self.primary_home_mortgage.principal_remaining if self.primary_home_mortgage else 0),
                'Primary_Home_Equity': round(primary_home_value - (self.primary_home_mortgage.principal_remaining if self.primary_home_mortgage else 0)),
                'Rental_Home_Value': round(current_rental_value_total),
                'Rental_Mortgage_Liability': round(sum(m.principal_remaining for m in self.rental_mortgages.values()) if self.rental_mortgages else 0),
                'Rental_Home_Equity': round(current_rental_value_total - (sum(m.principal_remaining for m in self.rental_mortgages.values()) if self.rental_mortgages else 0)),
                'Total_Home_Equity': round((primary_home_value - (self.primary_home_mortgage.principal_remaining if self.primary_home_mortgage else 0)) + (current_rental_value_total - (sum(m.principal_remaining for m in self.rental_mortgages.values()) if self.rental_mortgages else 0)))
            })
            
            # Update for next iteration
            # Carry forward this year's tax bill to be paid next year
            previous_year_taxes = tax_bill
            p1_age += 1
            p2_age += 1
            inflation_idx *= (1 + self.inputs['inflation_rate'])
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Save to file
        output_file = f"sim_{self.config_name}.csv"
        try:
            df.to_csv(output_file, index=False)
            if verbose:
                print(f"Simulation complete. Saved to {output_file}\n")
        except Exception as e:
            if verbose:
                print(f"Warning: Could not save CSV: {e}\n")
        
        # Display summary
        if verbose:
            print("=" * 100)
            print("RETIREMENT SIMULATION SUMMARY (values in thousands)")
            print("=" * 100)
            
            display_cols = ['Year', 'P1_Age', 'P2_Age', 'Total_Income', 'Cash_Need',
                           'Ord_Income', 'Tax_Bill', 'Net_Worth']
            df_display = df[display_cols].copy()
            scale_cols = [c for c in df_display.columns if c not in ['Year', 'P1_Age', 'P2_Age']]
            df_display[scale_cols] = (df_display[scale_cols] / 1000).round(1)
            
            print(df_display.head(20).to_string(index=False))
            print("\n...")
            print(df_display.tail(5).to_string(index=False))
        
        return df


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'nisha.csv'
    sim = RetirementSimulator(config_file=config_file, year=2025)
    sim.run(verbose=True)
