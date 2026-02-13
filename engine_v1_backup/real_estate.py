class Mortgage:
    """
    Manages mortgage calculations and amortization tracking.
    Supports mortgages on primary home and rental properties.
    """
    
    def __init__(self, principal_remaining, annual_interest_rate, years_remaining):
        """
        Initialize mortgage.
        
        Args:
            principal_remaining: Current principal balance
            annual_interest_rate: Annual interest rate (e.g., 0.065 for 6.5%)
            years_remaining: Years left on the mortgage
        """
        self.principal_remaining = max(0, principal_remaining)
        self.annual_interest_rate = max(0, annual_interest_rate)
        self.years_remaining = max(0, years_remaining)
        self.original_principal = self.principal_remaining
        self.months_remaining = int(self.years_remaining * 12)
        self.monthly_payment = 0
        self.interest_paid_this_year = 0
        self.principal_paid_this_year = 0
        
        self._calculate_monthly_payment()
    
    def _calculate_monthly_payment(self):
        """Calculate monthly mortgage payment using standard formula."""
        if self.principal_remaining <= 0 or self.months_remaining <= 0:
            self.monthly_payment = 0
            return
        
        monthly_rate = self.annual_interest_rate / 12
        
        if monthly_rate == 0:
            # No interest rate - just divide principal by remaining months
            self.monthly_payment = self.principal_remaining / self.months_remaining
        else:
            # Standard mortgage payment formula: P = L[c(1+c)^n]/[(1+c)^n-1]
            numerator = monthly_rate * ((1 + monthly_rate) ** self.months_remaining)
            denominator = ((1 + monthly_rate) ** self.months_remaining) - 1
            self.monthly_payment = self.principal_remaining * (numerator / denominator)
    
    def get_annual_payment(self):
        """Get total annual mortgage payment."""
        return self.monthly_payment * 12
    
    def make_payment(self, num_months=12):
        """
        Process mortgage payments for specified months.
        Updates principal, tracks interest and principal paid.
        
        Args:
            num_months: Number of months to process (default 12 for annual)
        """
        self.interest_paid_this_year = 0
        self.principal_paid_this_year = 0
        
        for _ in range(num_months):
            if self.principal_remaining <= 0 or self.monthly_payment <= 0:
                break
            
            monthly_rate = self.annual_interest_rate / 12
            interest_payment = self.principal_remaining * monthly_rate
            principal_payment = self.monthly_payment - interest_payment
            
            # Ensure we don't overpay principal
            if principal_payment > self.principal_remaining:
                principal_payment = self.principal_remaining
                interest_payment = self.monthly_payment - principal_payment
            
            self.principal_remaining -= principal_payment
            self.interest_paid_this_year += interest_payment
            self.principal_paid_this_year += principal_payment
            
            self.principal_remaining = max(0, self.principal_remaining)
        
        # Recalculate months remaining and payment
        if self.principal_remaining > 0:
            self.months_remaining = max(0, self.months_remaining - num_months)
            self.years_remaining = self.months_remaining / 12
            if self.months_remaining > 0 and self.annual_interest_rate > 0:
                self._calculate_monthly_payment()
        else:
            self.months_remaining = 0
            self.years_remaining = 0
            self.monthly_payment = 0
    
    def is_paid_off(self):
        """Check if mortgage is fully paid."""
        return self.principal_remaining <= 0
    
    def get_status(self):
        """Get current mortgage status as dict."""
        return {
            'principal_remaining': self.principal_remaining,
            'interest_paid_this_year': self.interest_paid_this_year,
            'principal_paid_this_year': self.principal_paid_this_year,
            'annual_payment': self.get_annual_payment(),
            'years_remaining': max(0, self.years_remaining),
            'paid_off': self.is_paid_off()
        }
