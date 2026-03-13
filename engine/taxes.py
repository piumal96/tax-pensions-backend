"""
Tax calculation engine — 2024 IRS values.
Handles federal income tax, FICA, LTCG, Social Security taxability,
and state income tax for all 50 states + DC.
"""

# ---------------------------------------------------------------------------
# 2024 State income tax data (MFJ brackets unless noted as flat rate)
# Brackets are (upper_limit, rate) cumulative.  [] = no income tax.
# ---------------------------------------------------------------------------
STATE_TAX_BRACKETS = {
    # No income tax states
    'Alaska': [], 'Florida': [], 'Nevada': [], 'New Hampshire': [],
    'South Dakota': [], 'Tennessee': [], 'Texas': [], 'Washington': [],
    'Wyoming': [],

    # Flat-rate states (single bracket spanning to $10M)
    'Arizona':       [(10_000_000, 0.025)],
    'Colorado':      [(10_000_000, 0.044)],
    'Georgia':       [(10_000_000, 0.0549)],
    'Idaho':         [(10_000_000, 0.058)],
    'Illinois':      [(10_000_000, 0.0495)],
    'Indiana':       [(10_000_000, 0.0305)],
    'Kentucky':      [(10_000_000, 0.045)],
    'Massachusetts': [(10_000_000, 0.05)],
    'Michigan':      [(10_000_000, 0.0405)],
    'Mississippi':   [(10_000_000, 0.05)],
    'North Carolina': [(10_000_000, 0.045)],
    'Pennsylvania':  [(10_000_000, 0.0307)],
    'Utah':          [(10_000_000, 0.0465)],

    # Progressive states — MFJ 2024
    'Alabama': [
        (1_000, 0.02), (6_000, 0.04), (10_000_000, 0.05),
    ],
    'Arkansas': [
        (4_999, 0.02), (9_999, 0.04), (10_000_000, 0.047),
    ],
    'California': [
        (20_824, 0.01), (49_368, 0.02), (77_918, 0.04),
        (108_162, 0.06), (136_700, 0.08), (698_274, 0.093),
        (837_922, 0.103), (1_000_000, 0.113), (10_000_000, 0.133),
    ],
    'Connecticut': [
        (20_000, 0.03), (100_000, 0.05), (200_000, 0.055),
        (400_000, 0.06), (10_000_000, 0.069),
    ],
    'Delaware': [
        (2_000, 0.0), (5_000, 0.022), (10_000, 0.039),
        (20_000, 0.048), (25_000, 0.052), (60_000, 0.0555),
        (10_000_000, 0.066),
    ],
    'Hawaii': [
        (4_800, 0.014), (9_600, 0.032), (19_200, 0.055),
        (28_800, 0.064), (38_400, 0.068), (48_000, 0.072),
        (72_000, 0.076), (96_000, 0.079), (300_000, 0.0825),
        (10_000_000, 0.09),
    ],
    'Iowa': [
        (6_210, 0.044), (31_050, 0.0482), (10_000_000, 0.057),
    ],
    'Kansas': [
        (30_000, 0.031), (60_000, 0.0525), (10_000_000, 0.057),
    ],
    'Louisiana': [
        (25_000, 0.0185), (100_000, 0.035), (10_000_000, 0.0425),
    ],
    'Maine': [
        (46_000, 0.058), (109_050, 0.0675), (10_000_000, 0.0715),
    ],
    'Maryland': [
        (1_000, 0.02), (2_000, 0.03), (3_000, 0.04),
        (100_000, 0.0475), (125_000, 0.05), (150_000, 0.0525),
        (250_000, 0.055), (10_000_000, 0.0575),
    ],
    'Minnesota': [
        (41_050, 0.0535), (163_060, 0.0705),
        (284_810, 0.0785), (10_000_000, 0.0985),
    ],
    'Missouri': [
        (1_121, 0.015), (2_242, 0.02), (3_363, 0.025),
        (4_484, 0.03), (5_605, 0.035), (6_726, 0.04),
        (7_847, 0.045), (8_968, 0.05), (10_000_000, 0.048),
    ],
    'Montana': [
        (3_600, 0.01), (6_300, 0.02), (9_700, 0.03),
        (13_000, 0.04), (16_800, 0.05), (21_600, 0.06),
        (10_000_000, 0.069),
    ],
    'Nebraska': [
        (6_860, 0.0246), (40_510, 0.0351), (10_000_000, 0.0664),
    ],
    'New Jersey': [
        (20_000, 0.014), (35_000, 0.0175), (40_000, 0.0245),
        (75_000, 0.035), (500_000, 0.05525), (1_000_000, 0.0637),
        (10_000_000, 0.1075),
    ],
    'New Mexico': [
        (8_000, 0.017), (16_000, 0.032), (24_000, 0.047),
        (315_000, 0.049), (10_000_000, 0.059),
    ],
    'New York': [
        (17_150, 0.04), (23_600, 0.045), (27_900, 0.0525),
        (161_550, 0.0585), (323_200, 0.0625), (2_155_350, 0.0685),
        (5_000_000, 0.0965), (25_000_000, 0.103), (10_000_000_000, 0.109),
    ],
    'North Dakota': [
        (44_725, 0.011), (108_225, 0.0204), (10_000_000, 0.029),
    ],
    'Ohio': [
        (26_050, 0.0), (100_000, 0.0275), (10_000_000, 0.035),
    ],
    'Oklahoma': [
        (2_000, 0.005), (5_000, 0.01), (7_500, 0.02),
        (9_800, 0.03), (12_200, 0.04), (10_000_000, 0.0475),
    ],
    'Oregon': [
        (18_400, 0.0475), (46_200, 0.0675),
        (250_000, 0.0875), (10_000_000, 0.099),
    ],
    'Rhode Island': [
        (73_450, 0.0375), (166_950, 0.0475), (10_000_000, 0.0599),
    ],
    'South Carolina': [
        (3_460, 0.0), (17_330, 0.03), (10_000_000, 0.065),
    ],
    'Vermont': [
        (73_400, 0.0335), (177_450, 0.066), (10_000_000, 0.076),
    ],
    'Virginia': [
        (3_000, 0.02), (5_000, 0.03), (17_000, 0.05),
        (10_000_000, 0.0575),
    ],
    'West Virginia': [
        (10_000, 0.0236), (25_000, 0.0315), (40_000, 0.063),
        (60_000, 0.07), (10_000_000, 0.065),
    ],
    'Wisconsin': [
        (18_280, 0.035), (36_520, 0.044),
        (402_070, 0.053), (10_000_000, 0.0765),
    ],
    'District of Columbia': [
        (10_000, 0.04), (40_000, 0.06), (60_000, 0.065),
        (250_000, 0.085), (500_000, 0.0925), (1_000_000, 0.1075),
        (10_000_000, 0.1075),
    ],
    # Fallback for any unlisted state: 5% flat
}

# States that exempt Social Security from state income tax
SS_EXEMPT_STATES = {
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California',
    'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Mississippi',
    'Nevada', 'New Hampshire', 'New Jersey', 'New York', 'North Carolina',
    'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'South Carolina',
    'South Dakota', 'Tennessee', 'Texas', 'Virginia', 'Washington',
    'Wisconsin', 'Wyoming', 'District of Columbia',
}


def _apply_brackets(taxable_income: float, brackets: list) -> float:
    """Apply progressive bracket table to taxable_income."""
    if not brackets or taxable_income <= 0:
        return 0.0
    tax = 0.0
    prev = 0.0
    for limit, rate in brackets:
        if taxable_income <= prev:
            break
        taxable_in_bracket = min(taxable_income, limit) - prev
        tax += taxable_in_bracket * rate
        prev = limit
    return tax


class TaxCalculator:
    """
    Federal + state tax calculations using 2024 IRS values.
    Handles ordinary income, LTCG, FICA, and state income tax.
    """

    # 2024 MFJ Federal Ordinary Income Brackets
    brackets_ordinary = [
        (23_200, 0.10), (94_300, 0.12), (201_050, 0.22),
        (383_900, 0.24), (487_450, 0.32), (731_200, 0.35),
        (10_000_000, 0.37),
    ]

    # 2024 MFJ Long-Term Capital Gains Brackets
    brackets_ltcg = [
        (94_050, 0.00), (583_750, 0.15), (10_000_000, 0.20),
    ]

    # 2024 MFJ Standard Deduction
    std_deduction = 29_200

    # FICA constants
    SS_WAGE_BASE = 168_600   # 2024 Social Security wage base
    SS_RATE_EMPLOYEE = 0.062
    MEDICARE_RATE = 0.0145
    MEDICARE_ADDITIONAL_RATE = 0.009   # Additional Medicare on wages > $250K MFJ

    def calculate_federal_tax(self, ordinary_income: float, capital_gains: float,
                              inflation_factor: float) -> float:
        """
        Federal income tax: ordinary income in brackets + LTCG stacked on top.
        Brackets are inflation-adjusted.
        """
        if ordinary_income + capital_gains <= 0:
            return 0.0

        adj_std_ded = self.std_deduction * inflation_factor
        adj_brackets_ord = [(lim * inflation_factor, rate)
                            for lim, rate in self.brackets_ordinary]
        adj_brackets_ltcg = [(lim * inflation_factor, rate)
                             for lim, rate in self.brackets_ltcg]

        taxable_ord = max(0.0, ordinary_income - adj_std_ded)
        ord_tax = _apply_brackets(taxable_ord, adj_brackets_ord)

        # LTCG stacked on top of ordinary income
        ltcg_floor = taxable_ord
        ltcg_ceiling = taxable_ord + capital_gains
        ltcg_tax = 0.0
        for limit, rate in adj_brackets_ltcg:
            if ltcg_ceiling > ltcg_floor and ltcg_floor < limit:
                fill = min(ltcg_ceiling, limit) - ltcg_floor
                ltcg_tax += fill * rate
                ltcg_floor = min(ltcg_ceiling, limit)
                if ltcg_floor >= ltcg_ceiling:
                    break

        return ord_tax + ltcg_tax

    # Keep old name as alias for backward compatibility
    def calculate_tax(self, ordinary_income: float, capital_gains: float,
                      inflation_factor: float) -> float:
        return self.calculate_federal_tax(ordinary_income, capital_gains, inflation_factor)

    def calculate_fica(self, wages_p1: float, wages_p2: float) -> float:
        """
        Employee FICA: Social Security (6.2% up to wage base) + Medicare (1.45% all wages).
        Additional 0.9% Medicare on combined wages above $250K MFJ.
        """
        def _fica_for(wages: float) -> float:
            ss = min(wages, self.SS_WAGE_BASE) * self.SS_RATE_EMPLOYEE
            medicare = wages * self.MEDICARE_RATE
            return ss + medicare

        fica = _fica_for(wages_p1) + _fica_for(wages_p2)
        combined_wages = wages_p1 + wages_p2
        if combined_wages > 250_000:
            fica += (combined_wages - 250_000) * self.MEDICARE_ADDITIONAL_RATE
        return fica

    def calculate_state_tax(self, ordinary_income: float, state: str,
                            inflation_factor: float,
                            exclude_ss: float = 0.0) -> float:
        """
        State income tax.  Brackets are NOT inflation-adjusted (states adjust
        at different rates; this approximation is acceptable for projections).
        `exclude_ss` is the SS amount already excluded from state taxable income
        for states that exempt SS.
        """
        if not state or ordinary_income <= 0:
            return 0.0

        brackets = STATE_TAX_BRACKETS.get(state)
        if brackets is None:
            # Unknown state: use 5% flat as a conservative estimate
            brackets = [(10_000_000, 0.05)]
        if not brackets:
            return 0.0  # No income tax state

        # Some states exempt SS income
        taxable = max(0.0, ordinary_income - exclude_ss)
        return _apply_brackets(taxable, brackets)

    def taxable_social_security(self, ss_total: float, provisional_income: float) -> float:
        """
        Federal formula: 0 / 50% / 85% of SS included in taxable income.
        MFJ thresholds: $32K / $44K.
        """
        if provisional_income <= 32_000:
            return 0.0
        elif provisional_income <= 44_000:
            return min(ss_total * 0.50, (provisional_income - 32_000) * 0.50)
        else:
            tier1 = min(ss_total * 0.50, 6_000)          # 50% on first $12K above $32K
            tier2 = (provisional_income - 44_000) * 0.85  # 85% above $44K
            return min(ss_total * 0.85, tier1 + tier2)
