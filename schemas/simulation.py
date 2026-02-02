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
