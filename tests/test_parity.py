import unittest
import pandas as pd
import numpy as np
import os
import sys

# Add parent dir to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from retirement_planner_yr import RetirementSimulator
from engine.core import run_deterministic, SimulationConfig
from engine.taxes import TaxCalculator

class TestParity(unittest.TestCase):
    def setUp(self):
        # Create a temp config file for the legacy simulator
        self.config_data = {
            'parameter': [
                'p1_start_age', 'p2_start_age', 'end_simulation_age', 'inflation_rate',
                'annual_spend_goal', 'filing_status', 'target_tax_bracket_rate', 'previous_year_taxes',
                'p1_employment_income', 'p1_employment_until_age',
                'p2_employment_income', 'p2_employment_until_age',
                'p1_ss_amount', 'p1_ss_start_age',
                'p2_ss_amount', 'p2_ss_start_age',
                'p1_pension', 'p1_pension_start_age',
                'p2_pension', 'p2_pension_start_age',
                'bal_taxable', 'bal_pretax_p1', 'bal_pretax_p2', 'bal_roth_p1', 'bal_roth_p2',
                'growth_rate_taxable', 'growth_rate_pretax_p1', 'growth_rate_pretax_p2',
                'growth_rate_roth_p1', 'growth_rate_roth_p2', 'taxable_basis_ratio',
                'primary_home_value', 'primary_home_growth_rate', 
                'primary_home_mortgage_principal', 'primary_home_mortgage_rate', 'primary_home_mortgage_years'
            ],
            'value': [
                65, 61, 95, 0.03,
                200000, 'MFJ', 0.24, 0,
                150000, 67,
                150000, 65,
                45000, 70,
                45000, 65,
                0, 67,
                0, 65,
                700000, 1250000, 1250000, 60000, 60000,
                0.07, 0.07, 0.07,
                0.07, 0.07, 0.75,
                0, 0.03,
                0, 0, 0
            ]
        }
        self.csv_path = 'test_parity_config.csv'
        pd.DataFrame(self.config_data).to_csv(self.csv_path, index=False)
        
        # Prepare params dict for new engine
        self.params_dict = dict(zip(self.config_data['parameter'], self.config_data['value']))
        # Ensure types match what the API would parse (float/int)
        for k, v in self.params_dict.items():
            try:
                self.params_dict[k] = float(v)
            except:
                pass

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def test_standard_strategy_parity(self):
        print("\nTesting Standard Strategy Parity...")
        
        # 1. Run Legacy
        legacy_sim = RetirementSimulator(config_file=self.csv_path, year=2025, strategy='standard')
        legacy_df = legacy_sim.run()
        
        # 2. Run New Engine
        new_config = SimulationConfig(start_year=2025, **self.params_dict)
        # Fix typing for int fields that might matter (ages)
        new_config.inputs['p1_start_age'] = int(new_config.inputs['p1_start_age'])
        new_config.inputs['p2_start_age'] = int(new_config.inputs['p2_start_age'])
        new_config.inputs['end_simulation_age'] = int(new_config.inputs['end_simulation_age'])
        
        new_records = run_deterministic(new_config, strategy_name='standard')
        new_df = pd.DataFrame(new_records)
        
        # 3. Visual Comparison for User
        print("\n" + "="*80)
        print(f"VISUAL CHECK: STANDARD STRATEGY")
        print("="*80)
        print(f"{'Year':<6} | {'Metric':<15} | {'Legacy Value':<15} | {'New Value':<15} | {'Diff':<10}")
        print("-" * 80)
        
        # Check first 3 years and last year for visual confirmation
        years_to_check = list(legacy_df['Year'].head(3)) + list(legacy_df['Year'].tail(1))
        
        metrics = ['Net_Worth', 'Bal_Taxable', 'WD_Taxable']
        
        for yr in years_to_check:
            leg_row = legacy_df[legacy_df['Year'] == yr].iloc[0]
            new_row = new_df[new_df['Year'] == yr].iloc[0]
            
            for m in metrics:
                leg_val = leg_row[m]
                new_val = new_row[m]
                diff = abs(leg_val - new_val)
                print(f"{int(yr):<6} | {m:<15} | {leg_val:>15,.2f} | {new_val:>15,.2f} | {diff:>10.2f}")
            print("-" * 80)

        # 4. Compare
        # Check specific key columns
        cols_to_check = ['Net_Worth', 'Bal_Taxable', 'Bal_PreTax_P1', 'Bal_PreTax_P2', 'Bal_Roth_P1', 'Bal_Roth_P2', 'WD_Taxable', 'WD_PreTax_P1']
        
        for col in cols_to_check:
            # Using a small tolerance for float comparison just in case of minor rounding diffs
            # but aiming for exact match since logic is identical
            try:
                pd.testing.assert_series_equal(legacy_df[col], new_df[col], check_names=False, rtol=1e-5)
                print(f"✅ {col} matches exactly.")
            except AssertionError as e:
                print(f"❌ {col} MISMATCH!")
                print("First 5 Legacy:")
                print(legacy_df[col].head())
                print("First 5 New:")
                print(new_df[col].head())
                raise e

    def test_taxable_first_strategy_parity(self):
        print("\nTesting Taxable First Strategy Parity...")
        
        # 1. Run Legacy
        legacy_sim = RetirementSimulator(config_file=self.csv_path, year=2025, strategy='taxable_first')
        legacy_df = legacy_sim.run()
        
        # 2. Run New Engine
        new_config = SimulationConfig(start_year=2025, **self.params_dict)
        # Fix typing 
        new_config.inputs['p1_start_age'] = int(new_config.inputs['p1_start_age'])
        new_config.inputs['p2_start_age'] = int(new_config.inputs['p2_start_age'])
        new_config.inputs['end_simulation_age'] = int(new_config.inputs['end_simulation_age'])
        
        new_records = run_deterministic(new_config, strategy_name='taxable_first')
        new_df = pd.DataFrame(new_records)

        # 3. Visual Comparison for User
        print("\n" + "="*80)
        print(f"VISUAL CHECK: TAXABLE_FIRST STRATEGY")
        print("="*80)
        print(f"{'Year':<6} | {'Metric':<15} | {'Legacy Value':<15} | {'New Value':<15} | {'Diff':<10}")
        print("-" * 80)
        
        years_to_check = list(legacy_df['Year'].head(3)) + list(legacy_df['Year'].tail(1))
        metrics = ['Net_Worth', 'Bal_Taxable', 'Roth_Conversion']
        
        for yr in years_to_check:
            leg_row = legacy_df[legacy_df['Year'] == yr].iloc[0]
            new_row = new_df[new_df['Year'] == yr].iloc[0]
            
            for m in metrics:
                leg_val = leg_row[m]
                new_val = new_row[m]
                diff = abs(leg_val - new_val)
                print(f"{int(yr):<6} | {m:<15} | {leg_val:>15,.2f} | {new_val:>15,.2f} | {diff:>10.2f}")
            print("-" * 80)
        
        # 4. Compare
        cols_to_check = ['Net_Worth', 'Bal_Taxable', 'Bal_PreTax_P1', 'Roth_Conversion']
        
        for col in cols_to_check:
            try:
                pd.testing.assert_series_equal(legacy_df[col], new_df[col], check_names=False, rtol=1e-5)
                print(f"✅ {col} matches exactly.")
            except AssertionError as e:
                print(f"❌ {col} MISMATCH!")
                raise e

if __name__ == '__main__':
    unittest.main()
