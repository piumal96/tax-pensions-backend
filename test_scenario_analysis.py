"""
Test scenario to identify calculation issues in the retirement planner.

Scenario: Young couple with:
- Small savings in the bank (taxable account)
- High salary
- Low spending
- Should be able to accumulate wealth over time

This test will help identify why simulations fail even with positive cash flow.
"""

import json
from schemas.simulation import SimulationParams
from services.simulation_service import run_simulation_service

def test_high_income_low_savings():
    """
    Test case: High income, low spending, small initial savings
    Expected: Should succeed - they're saving money each year
    """
    
    params = {
        # Demographics
        "p1_start_age": 30,
        "p2_start_age": 28,
        "end_simulation_age": 95,
        "inflation_rate": 0.03,
        
        # Spending & Tax
        "annual_spend_goal": 60000,  # Low spending
        "filing_status": "MFJ",
        "target_tax_bracket_rate": 0.22,
        "previous_year_taxes": 15000,
        
        # Employment - HIGH INCOME
        "p1_employment_income": 150000,  # $150k salary
        "p1_employment_until_age": 65,
        "p2_employment_income": 120000,  # $120k salary
        "p2_employment_until_age": 65,
        
        # Social Security
        "p1_ss_amount": 35000,
        "p1_ss_start_age": 67,
        "p2_ss_amount": 30000,
        "p2_ss_start_age": 67,
        
        # Pensions
        "p1_pension": 0,
        "p1_pension_start_age": 67,
        "p2_pension": 0,
        "p2_pension_start_age": 67,
        
        # Account Balances - SMALL STARTING AMOUNT
        "bal_taxable": 50000,  # Only $50k in taxable
        "bal_pretax_p1": 100000,  # $100k in 401k
        "bal_pretax_p2": 80000,   # $80k in 401k
        "bal_roth_p1": 0,
        "bal_roth_p2": 0,
        
        # Growth Rates
        "growth_rate_taxable": 0.07,
        "growth_rate_pretax_p1": 0.07,
        "growth_rate_pretax_p2": 0.07,
        "growth_rate_roth_p1": 0.07,
        "growth_rate_roth_p2": 0.07,
        "taxable_basis_ratio": 0.8,
    }
    
    print("=" * 80)
    print("TEST SCENARIO: High Income, Low Spending, Small Savings")
    print("=" * 80)
    print(f"\nInitial Setup:")
    print(f"  Ages: P1={params['p1_start_age']}, P2={params['p2_start_age']}")
    print(f"  Combined Income: ${params['p1_employment_income'] + params['p2_employment_income']:,}")
    print(f"  Annual Spending: ${params['annual_spend_goal']:,}")
    print(f"  Starting Taxable: ${params['bal_taxable']:,}")
    print(f"  Starting 401k Total: ${params['bal_pretax_p1'] + params['bal_pretax_p2']:,}")
    print(f"  Expected Annual Surplus (before taxes): ${params['p1_employment_income'] + params['p2_employment_income'] - params['annual_spend_goal']:,}")
    
    try:
        sim_params = SimulationParams(**params)
        results = run_simulation_service(sim_params)
        
        if results['success']:
            print("\n✓ Simulation completed successfully")
            
            # Analyze first 10 years
            standard_results = results['scenarios']['standard']['results']
            
            print("\n" + "=" * 80)
            print("YEAR-BY-YEAR ANALYSIS (First 10 Years)")
            print("=" * 80)
            
            for i, year_data in enumerate(standard_results[:10]):
                year = year_data['Year']
                total_income = year_data['Total_Income']
                cash_need = year_data['Cash_Need']
                bal_taxable = year_data['Bal_Taxable']
                net_worth = year_data['Net_Worth']
                tax_bill = year_data['Tax_Bill']
                
                # Calculate surplus/deficit
                surplus = total_income - cash_need
                
                print(f"\nYear {year} (Ages: {year_data['P1_Age']}/{year_data['P2_Age']})")
                print(f"  Income: ${total_income:,.0f}")
                print(f"  Cash Need (Spend + Taxes): ${cash_need:,.0f}")
                print(f"  Surplus/Deficit: ${surplus:,.0f}")
                print(f"  Tax Bill: ${tax_bill:,.0f}")
                print(f"  Taxable Balance: ${bal_taxable:,.0f}")
                print(f"  Net Worth: ${net_worth:,.0f}")
                
                # Check for problems
                if bal_taxable < 0:
                    print(f"  ⚠️  NEGATIVE TAXABLE BALANCE!")
                if surplus > 0 and bal_taxable < params['bal_taxable']:
                    print(f"  ⚠️  PROBLEM: Positive surplus but taxable balance decreased!")
            
            # Check final year
            final_year = standard_results[-1]
            print("\n" + "=" * 80)
            print(f"FINAL YEAR ({final_year['Year']}, Age {final_year['P1_Age']})")
            print("=" * 80)
            print(f"  Net Worth: ${final_year['Net_Worth']:,.0f}")
            if final_year['Net_Worth'] > 0:
                print("  ✓ Simulation succeeded - positive net worth at end")
            else:
                print("  ✗ Simulation failed - ran out of money")
                
        else:
            print("\n✗ Simulation failed")
            print(f"Results: {results}")
            
    except Exception as e:
        print(f"\n✗ Error running simulation: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)


def test_edge_case_no_pretax_contributions():
    """
    Test the issue where employment income is not being properly added to accounts.
    """
    print("\n" + "=" * 80)
    print("ISSUE ANALYSIS: Where does employment income go?")
    print("=" * 80)
    
    params = {
        "p1_start_age": 30,
        "p2_start_age": 30,
        "end_simulation_age": 35,  # Just 5 years
        "inflation_rate": 0.0,  # No inflation for easier math
        "annual_spend_goal": 50000,
        "filing_status": "MFJ",
        "target_tax_bracket_rate": 0.22,
        "previous_year_taxes": 10000,
        "p1_employment_income": 100000,
        "p1_employment_until_age": 65,
        "p2_employment_income": 100000,
        "p2_employment_until_age": 65,
        "p1_ss_amount": 0,
        "p1_ss_start_age": 67,
        "p2_ss_amount": 0,
        "p2_ss_start_age": 67,
        "p1_pension": 0,
        "p1_pension_start_age": 67,
        "p2_pension": 0,
        "p2_pension_start_age": 67,
        "bal_taxable": 10000,  # Very small starting balance
        "bal_pretax_p1": 0,
        "bal_pretax_p2": 0,
        "bal_roth_p1": 0,
        "bal_roth_p2": 0,
        "growth_rate_taxable": 0.0,  # No growth for easier math
        "growth_rate_pretax_p1": 0.0,
        "growth_rate_pretax_p2": 0.0,
        "growth_rate_roth_p1": 0.0,
        "growth_rate_roth_p2": 0.0,
        "taxable_basis_ratio": 1.0,  # All basis, no capital gains
    }
    
    print("\nSimplified scenario:")
    print(f"  Combined Income: $200,000/year")
    print(f"  Spending: $50,000/year")
    print(f"  Starting Balance: $10,000")
    print(f"  Expected after 1 year: ~$150,000+ in accounts")
    print(f"  (200k income - 50k spend - ~40k taxes = ~110k surplus)")
    
    try:
        sim_params = SimulationParams(**params)
        results = run_simulation_service(sim_params)
        
        if results['success']:
            standard_results = results['scenarios']['standard']['results']
            
            print("\n" + "-" * 80)
            for year_data in standard_results:
                year = year_data['Year']
                emp_p1 = year_data['Employment_P1']
                emp_p2 = year_data['Employment_P2']
                spend = year_data['Spend_Goal']
                taxes = year_data['Tax_Bill']
                prev_taxes = year_data['Previous_Taxes']
                cash_need = year_data['Cash_Need']
                bal_taxable = year_data['Bal_Taxable']
                total_income = year_data['Total_Income']
                wd_taxable = year_data['WD_Taxable']
                
                print(f"\nYear {year}:")
                print(f"  Employment: ${emp_p1 + emp_p2:,.0f}")
                print(f"  Total Income: ${total_income:,.0f}")
                print(f"  Spending Goal: ${spend:,.0f}")
                print(f"  Previous Year Taxes Paid: ${prev_taxes:,.0f}")
                print(f"  Cash Need: ${cash_need:,.0f}")
                print(f"  Taxable Withdrawal: ${wd_taxable:,.0f}")
                print(f"  Current Year Tax Bill: ${taxes:,.0f}")
                print(f"  Taxable Balance: ${bal_taxable:,.0f}")
                print(f"  Math Check: Income({total_income:.0f}) - CashNeed({cash_need:.0f}) = {total_income - cash_need:.0f}")
                
                if total_income > cash_need:
                    expected_increase = total_income - cash_need
                    print(f"  ⚠️  ISSUE: We have surplus of ${expected_increase:,.0f} but it's not being added to accounts!")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_high_income_low_savings()
    test_edge_case_no_pretax_contributions()
