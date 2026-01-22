import pandas as pd
import numpy as np
import sys
import os

class RetirementSimulator:
    """
    Simplified retirement simulator with:
    - Individual pretax and roth accounts per person (p1, p2)
    - Joint taxable account
    - Individual employment income until stated age
    - Previous year tax tracking
    - Step-by-step withdrawal strategy with roth conversions
    """
    
    def __init__(self, config_file='nisha.csv', year=2025):
        self.year = year
        self.config_name = os.path.splitext(os.path.basename(config_file))[0]
        
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

    def get_rmd_factor(self, age):
        """Get RMD divisor for age."""
        if age < 73:
            return 0
        if age >= 120:
            return 2.0
        return self.rmd_table.get(age, 27.4 - (age - 72))

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

    def get_bracket_room(self, current_ord_income, inflation_factor, target_rate):
        """
        How much room is left in the target tax bracket?
        This tells us how much we can convert to Roth without going above the bracket.
        """
        adj_std_ded = self.std_deduction * inflation_factor
        taxable_income = max(0, current_ord_income - adj_std_ded)
        
        adj_brackets = [(lim * inflation_factor, rate) for lim, rate in self.brackets_ordinary]
        
        target_limit = 0
        for limit, rate in adj_brackets:
            if rate == target_rate:
                target_limit = limit
                break
        
        if target_limit == 0:
            return 0
        
        room = max(0, target_limit - taxable_income)
        return room

    def run(self, verbose=False):
        """Run the retirement simulation."""
        
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
        
        inflation_idx = 1.0
        previous_year_taxes = self.inputs.get('previous_year_taxes', 0)
        
        records = []
        year = self.year
        
        while p1_age <= end_age:
            year += 1
            
            # --- 1. Account Growth ---
            b_taxable *= (1 + self.inputs['growth_rate_taxable'])
            b_pretax_p1 *= (1 + self.inputs['growth_rate_pretax_p1'])
            b_pretax_p2 *= (1 + self.inputs['growth_rate_pretax_p2'])
            b_roth_p1 *= (1 + self.inputs['growth_rate_roth_p1'])
            b_roth_p2 *= (1 + self.inputs['growth_rate_roth_p2'])
            
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
            
            # --- 3. Calculate Cash Need ---
            # Cash need = spending goal + taxes owed from previous year
            spend_goal = self.inputs['annual_spend_goal'] * inflation_idx
            cash_need = spend_goal + previous_year_taxes
            
            # --- 4. Withdrawal Strategy (Step by Step) ---
            # Priority order:
            # 1. Employment income
            # 2. Social Security
            # 3. Pensions
            # 4. RMDs (forced, older person first)
            # 5. Voluntary pretax (older person first)
            # 6. Taxable
            # 7. Roth (P1 first, then P2)
            # 8. Fill remaining bracket with Roth conversion
            
            total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total
            
            wd_pretax_p1 = 0
            wd_pretax_p2 = 0
            wd_roth_p1 = 0
            wd_roth_p2 = 0
            wd_taxable = 0
            roth_conversion = 0
            conv_p1 = 0
            conv_p2 = 0
            
            # Shortfall after income, RMDs
            shortfall = cash_need - (emp_p1 + emp_p2 + ss_total + pens_total + rmd_total)
            
            if shortfall > 0:
                # Take from pretax - older person first
                if p1_age >= p2_age:
                    # P1 is older
                    take_p1 = min(shortfall, max(0, b_pretax_p1 - rmd_p1))
                    wd_pretax_p1 = take_p1
                    shortfall -= take_p1
                    
                    if shortfall > 0:
                        take_p2 = min(shortfall, max(0, b_pretax_p2 - rmd_p2))
                        wd_pretax_p2 = take_p2
                        shortfall -= take_p2
                else:
                    # P2 is older
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
            
            # --- 5. Roth Conversion (Fill the bracket after main withdrawals) ---
            # Calculate current ordinary income from all sources
            current_ord_income = (emp_p1 + emp_p2 + ss_total + pens_total + 
                                 rmd_total + wd_pretax_p1 + wd_pretax_p2)
            
            # How much room left in target bracket?
            bracket_room = self.get_bracket_room(current_ord_income, inflation_idx, 
                                                self.inputs['target_tax_bracket_rate'])
            
            # How much pretax is left?
            pretax_left_p1 = max(0, b_pretax_p1 - rmd_p1 - wd_pretax_p1)
            pretax_left_p2 = max(0, b_pretax_p2 - rmd_p2 - wd_pretax_p2)
            pretax_left_total = pretax_left_p1 + pretax_left_p2
            
            # Convert up to bracket room (older person first)
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
            
            # --- 6. Update Account Balances ---
            b_pretax_p1 -= (rmd_p1 + wd_pretax_p1 + conv_p1)
            b_pretax_p2 -= (rmd_p2 + wd_pretax_p2 + conv_p2)
            b_roth_p1 += conv_p1
            b_roth_p1 -= wd_roth_p1
            b_roth_p2 += conv_p2
            b_roth_p2 -= wd_roth_p2
            b_taxable -= wd_taxable
            
            # --- 7. Calculate Taxes ---
            # Ordinary income includes employment, SS, pensions, RMDs, pretax withdrawals, conversions
            final_ord_income = (emp_p1 + emp_p2 + ss_total + pens_total + 
                               rmd_total + wd_pretax_p1 + wd_pretax_p2 + roth_conversion)
            
            # Capital gains from taxable withdrawal
            basis_ratio = self.inputs['taxable_basis_ratio']
            capital_gains = wd_taxable * (1 - basis_ratio)
            
            # Calculate total tax
            tax_bill = self.calculate_tax(final_ord_income, capital_gains, inflation_idx)
            
            # IMPORTANT: Taxes are paid NEXT year, not this year
            # This year's tax_bill is added to next year's cash_need via previous_year_taxes
            # Therefore, do NOT deduct taxes from accounts this year
            taxes_paid = 0
            
            # --- 8. Record Results ---
            net_worth = b_taxable + b_pretax_p1 + b_pretax_p2 + b_roth_p1 + b_roth_p2
            
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
                'Net_Worth': round(max(0, net_worth))
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
