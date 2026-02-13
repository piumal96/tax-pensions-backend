from abc import ABC, abstractmethod

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
        
        # Note: calling static helper or self helper. 
        # Refactoring Note: _get_bracket_room was instance method.
        # We'll make it static or instance. Here we keep as is but need to implement it.
        
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
        # Note: reusing helper from StandardStrategy or mixin would be better, but copying _get_bracket_room here for now to avoid mixin complexity
        # Actually I can copy the method here as well.
        
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
