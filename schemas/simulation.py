from typing import Optional
from pydantic import BaseModel, Field

class SimulationParams(BaseModel):
    """Complete simulation parameters with validation"""
    # Demographics
    p1_start_age: int = Field(ge=0, le=100)
    p2_start_age: int = Field(ge=0, le=100)
    end_simulation_age: int = Field(ge=0, le=120)
    inflation_rate: float = Field(ge=0, le=0.5)
    
    # Spending & Tax
    annual_spend_goal: float = Field(ge=0)
    filing_status: Optional[str] = 'MFJ'
    target_tax_bracket_rate: float = Field(ge=0, le=1, default=0.24)
    previous_year_taxes: Optional[float] = Field(ge=0, default=0)
    
    # Employment
    p1_employment_income: float = Field(ge=0, default=0)
    p1_employment_until_age: int = Field(ge=0, le=100, default=65)
    p2_employment_income: float = Field(ge=0, default=0)
    p2_employment_until_age: int = Field(ge=0, le=100, default=65)
    
    # Social Security
    p1_ss_amount: float = Field(ge=0, default=0)
    p1_ss_start_age: int = Field(ge=62, le=75, default=67)
    p2_ss_amount: float = Field(ge=0, default=0)
    p2_ss_start_age: int = Field(ge=62, le=75, default=67)
    
    # Pensions
    p1_pension: float = Field(ge=0, default=0)
    p1_pension_start_age: int = Field(ge=0, le=100, default=65)
    p2_pension: float = Field(ge=0, default=0)
    p2_pension_start_age: int = Field(ge=0, le=100, default=65)
    
    # Account Balances
    bal_taxable: float = Field(ge=0)
    bal_pretax_p1: float = Field(ge=0)
    bal_pretax_p2: float = Field(ge=0)
    bal_roth_p1: float = Field(ge=0)
    bal_roth_p2: float = Field(ge=0)
    
    # Growth Rates
    growth_rate_taxable: float = Field(ge=-0.5, le=0.5)
    growth_rate_pretax_p1: float = Field(ge=-0.5, le=0.5)
    growth_rate_pretax_p2: float = Field(ge=-0.5, le=0.5)
    growth_rate_roth_p1: float = Field(ge=-0.5, le=0.5)
    growth_rate_roth_p2: float = Field(ge=-0.5, le=0.5)
    taxable_basis_ratio: float = Field(ge=0, le=1)
    
    # 401k Contribution Settings (NEW - for accumulation phase)
    p1_401k_contribution_rate: Optional[float] = Field(ge=0, le=1, default=0.15)
    p1_401k_employer_match_rate: Optional[float] = Field(ge=0, le=0.15, default=0.05)
    p1_401k_is_roth: Optional[bool] = Field(default=False)
    
    p2_401k_contribution_rate: Optional[float] = Field(ge=0, le=1, default=0.15)
    p2_401k_employer_match_rate: Optional[float] = Field(ge=0, le=0.15, default=0.05)
    p2_401k_is_roth: Optional[bool] = Field(default=False)
    
    # Strategy optimization
    auto_optimize_roth_traditional: Optional[bool] = Field(default=True)
    
    # Debts & Loans
    student_loan_balance: Optional[float] = Field(ge=0, default=0)
    student_loan_rate: Optional[float] = Field(ge=0, le=0.3, default=0.05)
    student_loan_payment: Optional[float] = Field(ge=0, default=0)
    
    car_loan_balance: Optional[float] = Field(ge=0, default=0)
    car_loan_payment: Optional[float] = Field(ge=0, default=0)
    car_loan_years: Optional[float] = Field(ge=0, le=10, default=0)
    
    credit_card_debt: Optional[float] = Field(ge=0, default=0)
    credit_card_payment: Optional[float] = Field(ge=0, default=0)
    credit_card_rate: Optional[float] = Field(ge=0, le=0.35, default=0.18)
    
    # Healthcare & Medical
    annual_medical_expenses: Optional[float] = Field(ge=0, default=0)
    medical_inflation_rate: Optional[float] = Field(ge=0, le=0.15, default=0.06)
    
    # Business Income
    business_income: Optional[float] = Field(ge=0, default=0)
    business_growth_rate: Optional[float] = Field(ge=-0.1, le=0.3, default=0.03)
    business_ends_at_age: Optional[int] = Field(ge=0, le=100, default=65)
    
    # Kids & Dependents
    num_children: Optional[int] = Field(ge=0, le=10, default=0)
    child_1_current_age: Optional[int] = Field(ge=0, le=30, default=0)
    child_2_current_age: Optional[int] = Field(ge=0, le=30, default=0)
    child_3_current_age: Optional[int] = Field(ge=0, le=30, default=0)
    child_4_current_age: Optional[int] = Field(ge=0, le=30, default=0)
    monthly_expense_per_child_0_5: Optional[float] = Field(ge=0, default=500)    # Infant/toddler
    monthly_expense_per_child_6_12: Optional[float] = Field(ge=0, default=800)   # Elementary
    monthly_expense_per_child_13_17: Optional[float] = Field(ge=0, default=1000) # Teen
    college_cost_per_year: Optional[float] = Field(ge=0, default=25000)          # Annual college cost
    
    # Other Income
    passive_income: Optional[float] = Field(ge=0, default=0)
    passive_income_growth_rate: Optional[float] = Field(ge=0, le=0.15, default=0.02)
    
    # Life Insurance
    life_insurance_premium: Optional[float] = Field(ge=0, default=0)
    life_insurance_type: Optional[str] = Field(default='none')  # none, term, whole
    life_insurance_term_ends_at_age: Optional[int] = Field(ge=0, le=100, default=65)
    
    # Housing - Rent
    monthly_rent: Optional[float] = Field(ge=0, default=0)
    rent_inflation_rate: Optional[float] = Field(ge=0, le=0.15, default=0.03)
    
    # Real Estate
    primary_home_value: Optional[float] = Field(ge=0, default=0)
    primary_home_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    primary_home_mortgage_principal: Optional[float] = Field(ge=0, default=0)
    primary_home_mortgage_rate: Optional[float] = Field(ge=0, le=0.5, default=0)
    primary_home_mortgage_years: Optional[float] = Field(ge=0, le=50, default=0)
    
    # Rental Properties
    rental_1_value: Optional[float] = Field(ge=0, default=0)
    rental_1_income: Optional[float] = Field(ge=0, default=0)
    rental_1_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_1_income_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_1_mortgage_principal: Optional[float] = Field(ge=0, default=0)
    rental_1_mortgage_rate: Optional[float] = Field(ge=0, le=0.5, default=0)
    rental_1_mortgage_years: Optional[float] = Field(ge=0, le=50, default=0)
    
    rental_2_value: Optional[float] = Field(ge=0, default=0)
    rental_2_income: Optional[float] = Field(ge=0, default=0)
    rental_2_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_2_income_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_2_mortgage_principal: Optional[float] = Field(ge=0, default=0)
    rental_2_mortgage_rate: Optional[float] = Field(ge=0, le=0.5, default=0)
    rental_2_mortgage_years: Optional[float] = Field(ge=0, le=50, default=0)


class MonteCarloParams(SimulationParams):
    """Extends simulation params with Monte Carlo specific fields"""
    volatility: float = Field(ge=0, le=1, default=0.15)
    num_simulations: int = Field(ge=1, le=1000, default=100)
