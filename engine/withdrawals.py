"""
Withdrawal strategies for the retirement simulation engine.

Both strategies now receive the FULL cash need (spend_goal + taxes + mortgage +
debt + medical + children + college + rent + insurance + one-time expenses)
so account balances are drawn down realistically.
"""
from abc import ABC, abstractmethod


def _full_cash_need(inputs: dict) -> float:
    """Sum every cash obligation from strategy_inputs."""
    return (
        inputs.get('spend_goal', 0)
        + inputs.get('previous_year_taxes', 0)
        + inputs.get('mortgage_payment', 0)
        + inputs.get('debt_payment', 0)
        + inputs.get('medical_expenses', 0)
        + inputs.get('child_expenses', 0)
        + inputs.get('college_expenses', 0)
        + inputs.get('rent', 0)
        + inputs.get('insurance', 0)
        + inputs.get('one_time_expenses', 0)
    )


def _get_bracket_room(current_ord_income: float, inflation_idx: float,
                      target_rate: float, brackets_ordinary: list,
                      std_deduction: float) -> float:
    """How much income can still be added before hitting the target bracket ceiling."""
    adj_std_ded = std_deduction * inflation_idx
    taxable_income = max(0.0, current_ord_income - adj_std_ded)
    adj_brackets = [(lim * inflation_idx, rate) for lim, rate in brackets_ordinary]
    target_limit = 0.0
    for limit, rate in adj_brackets:
        if rate == target_rate:
            target_limit = limit
            break
    if target_limit == 0.0:
        return 0.0
    return max(0.0, target_limit - taxable_income)


class WithdrawalStrategy(ABC):
    @abstractmethod
    def execute(self, inputs, account_balances, income_sources,
                inflation_idx, rmd_table, brackets_ordinary, std_deduction):
        pass


class StandardStrategy(WithdrawalStrategy):
    """
    Draw order: (RMDs forced) → PreTax (older first) → Taxable → Roth.
    Fill remaining bracket with Roth conversions.
    Uses FULL cash need so every real expense drives account drawdowns.
    """

    def execute(self, inputs, account_balances, income_sources,
                inflation_idx, rmd_table, brackets_ordinary, std_deduction):

        b_taxable, b_pretax_p1, b_pretax_p2, b_roth_p1, b_roth_p2 = account_balances
        emp_p1, emp_p2, ss_total, pens_total, rmd_p1, rmd_p2 = income_sources
        p1_age, p2_age = inputs['p1_age'], inputs['p2_age']

        rmd_total    = rmd_p1 + rmd_p2
        total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total
        cash_need    = _full_cash_need(inputs)
        shortfall    = max(0.0, cash_need - total_income)

        wd_pretax_p1 = wd_pretax_p2 = 0.0
        wd_roth_p1 = wd_roth_p2 = 0.0
        wd_taxable  = 0.0
        conv_p1 = conv_p2 = roth_conversion = 0.0

        # PreTax — older person first
        if shortfall > 0:
            if p1_age >= p2_age:
                t = min(shortfall, max(0.0, b_pretax_p1 - rmd_p1))
                wd_pretax_p1 = t;  shortfall -= t
                if shortfall > 0:
                    t = min(shortfall, max(0.0, b_pretax_p2 - rmd_p2))
                    wd_pretax_p2 = t;  shortfall -= t
            else:
                t = min(shortfall, max(0.0, b_pretax_p2 - rmd_p2))
                wd_pretax_p2 = t;  shortfall -= t
                if shortfall > 0:
                    t = min(shortfall, max(0.0, b_pretax_p1 - rmd_p1))
                    wd_pretax_p1 = t;  shortfall -= t

        # Taxable
        if shortfall > 0:
            wd_taxable = min(shortfall, b_taxable);  shortfall -= wd_taxable

        # Roth
        if shortfall > 0:
            t = min(shortfall, b_roth_p1);  wd_roth_p1 = t;  shortfall -= t
        if shortfall > 0:
            t = min(shortfall, b_roth_p2);  wd_roth_p2 = t;  shortfall -= t

        # Roth conversion — fill target bracket
        current_ord = (emp_p1 + emp_p2 + ss_total + pens_total
                       + rmd_total + wd_pretax_p1 + wd_pretax_p2)
        room = _get_bracket_room(current_ord, inflation_idx,
                                 inputs['target_tax_bracket_rate'],
                                 brackets_ordinary, std_deduction)
        pl1 = max(0.0, b_pretax_p1 - rmd_p1 - wd_pretax_p1)
        pl2 = max(0.0, b_pretax_p2 - rmd_p2 - wd_pretax_p2)
        if room > 0 and (pl1 + pl2) > 0:
            amt = min(room, pl1 + pl2)
            if p1_age >= p2_age:
                conv_p1 = min(amt, pl1);  amt -= conv_p1
                conv_p2 = min(amt, pl2)
            else:
                conv_p2 = min(amt, pl2);  amt -= conv_p2
                conv_p1 = min(amt, pl1)
            roth_conversion = conv_p1 + conv_p2

        return dict(wd_pretax_p1=wd_pretax_p1, wd_pretax_p2=wd_pretax_p2,
                    wd_taxable=wd_taxable, wd_roth_p1=wd_roth_p1, wd_roth_p2=wd_roth_p2,
                    roth_conversion=roth_conversion, conv_p1=conv_p1, conv_p2=conv_p2)


class TaxableFirstStrategy(WithdrawalStrategy):
    """
    Draw order: Taxable → Roth → PreTax (with room left for conversions).
    Then fill bracket with Roth conversions.
    Uses FULL cash need.
    """

    def execute(self, inputs, account_balances, income_sources,
                inflation_idx, rmd_table, brackets_ordinary, std_deduction):

        b_taxable, b_pretax_p1, b_pretax_p2, b_roth_p1, b_roth_p2 = account_balances
        emp_p1, emp_p2, ss_total, pens_total, rmd_p1, rmd_p2 = income_sources
        p1_age, p2_age = inputs['p1_age'], inputs['p2_age']

        rmd_total    = rmd_p1 + rmd_p2
        total_income = emp_p1 + emp_p2 + ss_total + pens_total + rmd_total
        cash_need    = _full_cash_need(inputs)
        remaining    = max(0.0, cash_need - total_income)

        wd_pretax_p1 = wd_pretax_p2 = 0.0
        wd_roth_p1 = wd_roth_p2 = 0.0
        wd_taxable  = 0.0
        conv_p1 = conv_p2 = roth_conversion = 0.0

        # Taxable first
        if remaining > 0:
            wd_taxable = min(remaining, b_taxable);  remaining -= wd_taxable

        # Roth next (tax-free)
        if remaining > 0:
            t = min(remaining, b_roth_p1);  wd_roth_p1 = t;  remaining -= t
        if remaining > 0:
            t = min(remaining, b_roth_p2);  wd_roth_p2 = t;  remaining -= t

        # PreTax last (leaves room for conversions)
        if remaining > 0:
            if p1_age >= p2_age:
                t = min(remaining, max(0.0, b_pretax_p1 - rmd_p1))
                wd_pretax_p1 = t;  remaining -= t
                if remaining > 0:
                    t = min(remaining, max(0.0, b_pretax_p2 - rmd_p2))
                    wd_pretax_p2 = t;  remaining -= t
            else:
                t = min(remaining, max(0.0, b_pretax_p2 - rmd_p2))
                wd_pretax_p2 = t;  remaining -= t
                if remaining > 0:
                    t = min(remaining, max(0.0, b_pretax_p1 - rmd_p1))
                    wd_pretax_p1 = t;  remaining -= t

        # Roth conversion
        current_ord = (emp_p1 + emp_p2 + ss_total + pens_total
                       + rmd_total + wd_pretax_p1 + wd_pretax_p2)
        room = _get_bracket_room(current_ord, inflation_idx,
                                 inputs['target_tax_bracket_rate'],
                                 brackets_ordinary, std_deduction)
        pl1 = max(0.0, b_pretax_p1 - rmd_p1 - wd_pretax_p1)
        pl2 = max(0.0, b_pretax_p2 - rmd_p2 - wd_pretax_p2)
        if room > 0 and (pl1 + pl2) > 0:
            amt = min(room, pl1 + pl2)
            if p1_age >= p2_age:
                conv_p1 = min(amt, pl1);  amt -= conv_p1
                conv_p2 = min(amt, pl2)
            else:
                conv_p2 = min(amt, pl2);  amt -= conv_p2
                conv_p1 = min(amt, pl1)
            roth_conversion = conv_p1 + conv_p2

        return dict(wd_pretax_p1=wd_pretax_p1, wd_pretax_p2=wd_pretax_p2,
                    wd_taxable=wd_taxable, wd_roth_p1=wd_roth_p1, wd_roth_p2=wd_roth_p2,
                    roth_conversion=roth_conversion, conv_p1=conv_p1, conv_p2=conv_p2)
