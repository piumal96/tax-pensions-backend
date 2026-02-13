"""
Debt tracking module for managing various types of debt (student loans, car loans, credit cards)
"""

class Debt:
    """
    Generic debt tracker with balance, payment, and interest.
    Handles amortization and payoff tracking.
    """
    
    def __init__(self, balance, monthly_payment, annual_rate=0, label="Debt"):
        """
        Initialize a debt.
        
        Args:
            balance: Current outstanding balance
            monthly_payment: Fixed monthly payment amount
            annual_rate: Annual interest rate (as decimal, e.g., 0.05 for 5%)
            label: Description of the debt (e.g., "Student Loan", "Car Loan")
        """
        self.initial_balance = balance
        self.balance = balance
        self.monthly_payment = monthly_payment
        self.annual_rate = annual_rate
        self.label = label
        self.total_paid = 0
        self.total_interest_paid = 0
    
    def make_payment(self, months=12):
        """
        Make debt payments for the specified number of months.
        Applies interest monthly and tracks principal reduction.
        
        Args:
            months: Number of months to pay (default 12 for annual simulation)
        
        Returns:
            tuple: (total_paid_this_period, interest_paid_this_period)
        """
        period_payment = 0
        period_interest = 0
        
        for _ in range(months):
            if self.balance <= 0:
                break
            
            # Calculate monthly interest
            monthly_interest = (self.balance * self.annual_rate) / 12
            
            # Determine actual payment (may be less than monthly_payment if balance is low)
            actual_payment = min(self.monthly_payment, self.balance + monthly_interest)
            
            # Split payment between interest and principal
            interest_portion = monthly_interest
            principal_portion = actual_payment - interest_portion
            
            # Update balance
            self.balance = max(0, self.balance - principal_portion)
            
            # Track totals
            period_payment += actual_payment
            period_interest += interest_portion
            self.total_paid += actual_payment
            self.total_interest_paid += interest_portion
        
        return period_payment, period_interest
    
    def get_annual_payment(self):
        """
        Get the total annual payment amount (12 months).
        Takes into account if debt will be paid off during the year.
        
        Returns:
            float: Total payment for the year
        """
        if self.balance <= 0:
            return 0
        
        # Estimate: monthly payment * 12, but don't exceed remaining balance + interest
        estimated_annual_interest = self.balance * self.annual_rate
        max_payment = self.balance + estimated_annual_interest
        
        return min(self.monthly_payment * 12, max_payment)
    
    def is_paid_off(self):
        """Check if debt is fully paid off"""
        return self.balance <= 0
    
    def get_status(self):
        """Get current debt status as dictionary"""
        return {
            'label': self.label,
            'balance': self.balance,
            'monthly_payment': self.monthly_payment,
            'annual_rate': self.annual_rate,
            'total_paid': self.total_paid,
            'total_interest_paid': self.total_interest_paid,
            'is_paid_off': self.is_paid_off()
        }


def initialize_debts(config):
    """
    Initialize all debts from configuration.
    
    Args:
        config: Dictionary with debt parameters
    
    Returns:
        list: List of Debt objects
    """
    debts = []
    
    # Student Loan
    if config.get('student_loan_balance', 0) > 0:
        student_debt = Debt(
            balance=config['student_loan_balance'],
            monthly_payment=config.get('student_loan_payment', 0),
            annual_rate=config.get('student_loan_rate', 0.05),
            label='Student Loan'
        )
        debts.append(student_debt)
    
    # Car Loan
    if config.get('car_loan_balance', 0) > 0:
        # Calculate monthly payment if not provided, using years remaining
        car_payment = config.get('car_loan_payment', 0)
        if car_payment == 0 and config.get('car_loan_years', 0) > 0:
            # Simple approximation: balance / (years * 12)
            # More accurate would use amortization formula, but we'll use provided payment
            car_payment = config['car_loan_balance'] / (config['car_loan_years'] * 12)
        
        car_debt = Debt(
            balance=config['car_loan_balance'],
            monthly_payment=car_payment,
            annual_rate=0.06,  # Assume 6% if not provided
            label='Car Loan'
        )
        debts.append(car_debt)
    
    # Credit Card Debt
    if config.get('credit_card_debt', 0) > 0:
        cc_debt = Debt(
            balance=config['credit_card_debt'],
            monthly_payment=config.get('credit_card_payment', 0),
            annual_rate=config.get('credit_card_rate', 0.18),
            label='Credit Card'
        )
        debts.append(cc_debt)
    
    return debts


def get_total_debt_payment(debts):
    """
    Calculate total annual debt payment across all debts.
    
    Args:
        debts: List of Debt objects
    
    Returns:
        float: Total annual payment
    """
    return sum(debt.get_annual_payment() for debt in debts)


def get_total_debt_balance(debts):
    """
    Calculate total remaining balance across all debts.
    
    Args:
        debts: List of Debt objects
    
    Returns:
        float: Total remaining balance
    """
    return sum(debt.balance for debt in debts)


def process_all_debt_payments(debts, months=12):
    """
    Process payments for all debts.
    
    Args:
        debts: List of Debt objects
        months: Number of months to process (default 12)
    
    Returns:
        tuple: (total_payment, total_interest, remaining_balance)
    """
    total_payment = 0
    total_interest = 0
    
    for debt in debts:
        if not debt.is_paid_off():
            payment, interest = debt.make_payment(months)
            total_payment += payment
            total_interest += interest
    
    remaining_balance = get_total_debt_balance(debts)
    
    return total_payment, total_interest, remaining_balance
