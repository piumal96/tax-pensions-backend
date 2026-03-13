class TaxCalculator:
    """
    Handles federal tax calculations using 2024 brackets.
    """
    
    def __init__(self):
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
