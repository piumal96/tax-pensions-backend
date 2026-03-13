"""
Optimal Contribution Strategy Module

This module implements the optimal allocation of surplus income during
accumulation years, mirroring the withdrawal strategy's tax optimization.
"""

class ContributionAllocator:
    """
    Allocates surplus income optimally across 401k, Roth, and taxable accounts.
    
    Strategy:
    1. Employer match first (free money)
    2. Max 401k (Roth vs Traditional based on tax arbitrage)
    3. IRA contributions (if enabled)
    4. Remainder to taxable (flexibility)
    """
    
    def __init__(self, tax_brackets, std_deduction):
        """
        Initialize with tax information.
        
        Args:
            tax_brackets: List of (limit, rate) tuples for ordinary income
            std_deduction: Standard deduction amount
        """
        self.tax_brackets = tax_brackets
        self.std_deduction = std_deduction
        
        # IRS limits for 2024
        self.irs_401k_limit = 23000
        self.irs_401k_catchup = 30500  # Age 50+
        self.irs_ira_limit = 7000
        self.irs_ira_catchup = 8000  # Age 50+
    
    def estimate_marginal_rate(self, ordinary_income, inflation_factor):
        """
        Estimate current marginal tax rate.
        
        Args:
            ordinary_income: Total ordinary income for the year
            inflation_factor: Inflation adjustment factor
            
        Returns:
            Estimated marginal tax rate (0-1)
        """
        adj_std_ded = self.std_deduction * inflation_factor
        taxable_income = max(0, ordinary_income - adj_std_ded)
        
        adj_brackets = [(lim * inflation_factor, rate) for lim, rate in self.tax_brackets]
        
        # Find which bracket we're in
        for limit, rate in adj_brackets:
            if taxable_income <= limit:
                return rate
        
        # If we exceed all brackets, return top rate
        return adj_brackets[-1][1]
    
    def allocate_surplus(self, surplus, config, ages, incomes, inflation_factor):
        """
        Allocate surplus income optimally.
        
        Args:
            surplus: Amount of surplus cash after expenses
            config: Simulation configuration
            ages: Tuple of (p1_age, p2_age)
            incomes: Tuple of (emp_p1, emp_p2) employment income
            inflation_factor: Current inflation adjustment
            
        Returns:
            Dictionary with allocation amounts:
            {
                'to_pretax_p1': float,
                'to_pretax_p2': float,
                'to_roth_p1': float,
                'to_roth_p2': float,
                'to_taxable': float,
                'tax_savings': float  # Amount saved in taxes
            }
        """
        p1_age, p2_age = ages
        emp_p1, emp_p2 = incomes
        
        # Get configuration parameters (with defaults)
        p1_contrib_rate = config.get('p1_401k_contribution_rate', 0.15)
        p2_contrib_rate = config.get('p2_401k_contribution_rate', 0.15)
        p1_match_rate = config.get('p1_401k_employer_match_rate', 0.05)
        p2_match_rate = config.get('p2_401k_employer_match_rate', 0.05)
        p1_match_cap = config.get('p1_401k_employer_match_cap', 0.06)  # Match up to 6% of salary
        p2_match_cap = config.get('p2_401k_employer_match_cap', 0.06)
        
        target_tax_rate = config.get('target_tax_bracket_rate', 0.24)
        enable_ira = config.get('enable_ira_contributions', False)  # Default False for simplicity
        force_roth = config.get('force_roth_401k', False)
        auto_optimize = config.get('auto_optimize_roth_traditional', True)
        
        # Calculate current marginal tax rate
        total_income = emp_p1 + emp_p2
        current_marginal_rate = self.estimate_marginal_rate(total_income, inflation_factor)
        
        # Determine whether to use Roth or Traditional
        if force_roth:
            use_roth = True
        elif auto_optimize:
            # Use Roth if current rate <= target retirement rate (tax arbitrage)
            use_roth = current_marginal_rate <= target_tax_rate
        else:
            # Default to Traditional for tax deferral
            use_roth = False
        
        # Initialize allocations
        to_pretax_p1 = 0
        to_pretax_p2 = 0
        to_roth_p1 = 0
        to_roth_p2 = 0
        to_taxable = 0
        tax_savings = 0
        
        remaining_surplus = surplus
        
        # --- PERSON 1 ALLOCATIONS ---
        if emp_p1 > 0 and p1_age < config.get('p1_employment_until_age', 65):
            # 1. Calculate employer match (up to cap)
            max_matched_contribution = emp_p1 * p1_match_cap
            employee_contribution_for_full_match = max_matched_contribution / p1_match_rate if p1_match_rate > 0 else 0
            
            # Employee contribution (capped at IRS limit and what's available)
            max_contrib = self.irs_401k_catchup if p1_age >= 50 else self.irs_401k_limit
            employee_contrib_p1 = min(
                emp_p1 * p1_contrib_rate,  # % of salary
                max_contrib,  # IRS limit
                remaining_surplus if not use_roth else remaining_surplus / (1 - current_marginal_rate)  # Available cash
            )
            
            # Employer match (proportional to employee contribution, up to cap)
            if employee_contrib_p1 >= employee_contribution_for_full_match:
                employer_match_p1 = max_matched_contribution
            else:
                employer_match_p1 = employee_contrib_p1 * p1_match_rate
            
            # Total going to 401k
            total_401k_p1 = employee_contrib_p1 + employer_match_p1
            
            # Allocate to Roth or Traditional
            if use_roth:
                to_roth_p1 += total_401k_p1
                # Roth contributions are post-tax, so they reduce surplus directly
                remaining_surplus -= employee_contrib_p1
            else:
                to_pretax_p1 += total_401k_p1
                # Traditional contributions are pre-tax, so they save taxes
                tax_savings += employee_contrib_p1 * current_marginal_rate
                # Net cost to surplus is after-tax equivalent
                remaining_surplus -= employee_contrib_p1 * (1 - current_marginal_rate)
        
        # --- PERSON 2 ALLOCATIONS ---
        if emp_p2 > 0 and p2_age < config.get('p2_employment_until_age', 65):
            max_matched_contribution = emp_p2 * p2_match_cap
            employee_contribution_for_full_match = max_matched_contribution / p2_match_rate if p2_match_rate > 0 else 0
            
            max_contrib = self.irs_401k_catchup if p2_age >= 50 else self.irs_401k_limit
            employee_contrib_p2 = min(
                emp_p2 * p2_contrib_rate,
                max_contrib,
                remaining_surplus if not use_roth else remaining_surplus / (1 - current_marginal_rate)
            )
            
            if employee_contrib_p2 >= employee_contribution_for_full_match:
                employer_match_p2 = max_matched_contribution
            else:
                employer_match_p2 = employee_contrib_p2 * p2_match_rate
            
            total_401k_p2 = employee_contrib_p2 + employer_match_p2
            
            if use_roth:
                to_roth_p2 += total_401k_p2
                remaining_surplus -= employee_contrib_p2
            else:
                to_pretax_p2 += total_401k_p2
                tax_savings += employee_contrib_p2 * current_marginal_rate
                remaining_surplus -= employee_contrib_p2 * (1 - current_marginal_rate)
        
        # --- IRA CONTRIBUTIONS (Optional) ---
        if enable_ira and remaining_surplus > 0:
            # Person 1 IRA
            if emp_p1 > 0:
                ira_limit_p1 = self.irs_ira_catchup if p1_age >= 50 else self.irs_ira_limit
                ira_contrib_p1 = min(
                    ira_limit_p1,
                    remaining_surplus / 2  # Split remaining between both
                )
                
                # IRA contributions typically go to Roth if we're using Roth strategy
                to_roth_p1 += ira_contrib_p1
                remaining_surplus -= ira_contrib_p1
            
            # Person 2 IRA
            if emp_p2 > 0:
                ira_limit_p2 = self.irs_ira_catchup if p2_age >= 50 else self.irs_ira_limit
                ira_contrib_p2 = min(
                    ira_limit_p2,
                    remaining_surplus
                )
                
                to_roth_p2 += ira_contrib_p2
                remaining_surplus -= ira_contrib_p2
        
        # --- REMAINDER TO TAXABLE ---
        # Remaining surplus goes to taxable account (already post-tax)
        to_taxable = max(0, remaining_surplus)
        
        return {
            'to_pretax_p1': to_pretax_p1,
            'to_pretax_p2': to_pretax_p2,
            'to_roth_p1': to_roth_p1,
            'to_roth_p2': to_roth_p2,
            'to_taxable': to_taxable,
            'tax_savings': tax_savings,
            'current_marginal_rate': current_marginal_rate,
            'strategy_used': 'Roth' if use_roth else 'Traditional'
        }


# Simpler version for immediate implementation
def allocate_surplus_simple(surplus, config, ages, incomes, inflation_factor, 
                           tax_brackets, std_deduction, target_tax_rate):
    """
    Simplified surplus allocation - suitable for immediate implementation.
    
    This version makes reasonable assumptions and doesn't require extensive configuration.
    
    Args:
        surplus: Surplus income after expenses and taxes
        config: Configuration dict
        ages: (p1_age, p2_age)
        incomes: (emp_p1, emp_p2)
        inflation_factor: Current inflation adjustment
        tax_brackets: Tax bracket list
        std_deduction: Standard deduction
        target_tax_rate: Target retirement tax rate
        
    Returns:
        Dict with allocation amounts
    """
    p1_age, p2_age = ages
    emp_p1, emp_p2 = incomes
    
    # Simple assumptions
    contrib_rate = 0.15  # 15% of salary
    match_rate = 0.05    # 5% employer match
    
    # Estimate current marginal rate (simple version)
    total_income = emp_p1 + emp_p2
    adj_std_ded = std_deduction * inflation_factor
    taxable = max(0, total_income - adj_std_ded)
    
    current_rate = 0.24  # Default to 24%
    adj_brackets = [(lim * inflation_factor, rate) for lim, rate in tax_brackets]
    for limit, rate in adj_brackets:
        if taxable <= limit:
            current_rate = rate
            break
    
    # Decide Roth vs Traditional
    use_roth = current_rate <= target_tax_rate
    
    # Calculate contributions
    to_pretax_p1 = 0
    to_pretax_p2 = 0
    to_roth_p1 = 0
    to_roth_p2 = 0
    
    remaining = surplus
    
    # P1 contributions
    if emp_p1 > 0 and p1_age < config.get('p1_employment_until_age', 65):
        contrib_p1 = min(emp_p1 * contrib_rate, 23000 if p1_age < 50 else 30500)
        match_p1 = emp_p1 * match_rate
        total_p1 = contrib_p1 + match_p1
        
        if use_roth:
            to_roth_p1 = total_p1
        else:
            to_pretax_p1 = total_p1
        
        remaining -= contrib_p1  # Employee contribution comes from surplus
    
    # P2 contributions  
    if emp_p2 > 0 and p2_age < config.get('p2_employment_until_age', 65):
        contrib_p2 = min(emp_p2 * contrib_rate, 23000 if p2_age < 50 else 30500)
        match_p2 = emp_p2 * match_rate
        total_p2 = contrib_p2 + match_p2
        
        if use_roth:
            to_roth_p2 = total_p2
        else:
            to_pretax_p2 = total_p2
        
        remaining -= contrib_p2
    
    # Remainder to taxable (after tax)
    to_taxable = remaining * (1 - current_rate) if not use_roth else remaining
    
    return {
        'to_pretax_p1': to_pretax_p1,
        'to_pretax_p2': to_pretax_p2,
        'to_roth_p1': to_roth_p1,
        'to_roth_p2': to_roth_p2,
        'to_taxable': to_taxable,
        'strategy_used': 'Roth' if use_roth else 'Traditional'
    }
