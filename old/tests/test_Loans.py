"""Tests for loan mechanics in the game engine."""

import unittest
from app.base import Player, PublicCompany, Loan


class LoanTests(unittest.TestCase):
    """Tests for the Loan dataclass and related functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Player.create("TestPlayer", 1000, 0)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player
        self.company.cash = 100

    def test_loan_creation(self):
        """Loan can be created with correct attributes."""
        loan = Loan(
            id="loan-1",
            principal=500,
            balance=500,
            interest_rate=0.05,
            lender=self.player,
            round_taken=1
        )
        self.assertEqual(loan.principal, 500)
        self.assertEqual(loan.balance, 500)
        self.assertEqual(loan.interest_rate, 0.05)
        self.assertEqual(loan.lender, self.player)
        self.assertEqual(loan.round_taken, 1)

    def test_loan_interest_accrual(self):
        """Interest accrues correctly on loan balance."""
        loan = Loan(
            id="loan-1",
            principal=1000,
            balance=1000,
            interest_rate=0.10,  # 10% interest
            lender=self.player,
            round_taken=1
        )

        loan.accrue_interest()
        self.assertEqual(loan.balance, 1100)  # 1000 * 1.10

        loan.accrue_interest()
        self.assertEqual(loan.balance, 1210)  # 1100 * 1.10

    def test_loan_partial_payment(self):
        """Partial loan payment reduces balance correctly."""
        loan = Loan(
            id="loan-1",
            principal=1000,
            balance=1000,
            interest_rate=0.05,
            lender=self.player,
            round_taken=1
        )

        actual_payment = loan.make_payment(300)
        self.assertEqual(actual_payment, 300)
        self.assertEqual(loan.balance, 700)
        self.assertFalse(loan.is_paid_off())

    def test_loan_full_payment(self):
        """Full loan payment sets balance to zero."""
        loan = Loan(
            id="loan-1",
            principal=500,
            balance=500,
            interest_rate=0.05,
            lender=self.player,
            round_taken=1
        )

        actual_payment = loan.make_payment(500)
        self.assertEqual(actual_payment, 500)
        self.assertEqual(loan.balance, 0)
        self.assertTrue(loan.is_paid_off())

    def test_loan_overpayment_capped(self):
        """Overpayment is capped at current balance."""
        loan = Loan(
            id="loan-1",
            principal=500,
            balance=200,
            interest_rate=0.05,
            lender=self.player,
            round_taken=1
        )

        actual_payment = loan.make_payment(300)
        self.assertEqual(actual_payment, 200)  # Only pays remaining balance
        self.assertEqual(loan.balance, 0)
        self.assertTrue(loan.is_paid_off())


class PublicCompanyLoanTests(unittest.TestCase):
    """Tests for loan methods on PublicCompany."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Player.create("TestPlayer", 1000, 0)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player
        self.company.cash = 100

    def test_take_loan_increases_company_cash(self):
        """Taking a loan increases company cash."""
        initial_cash = self.company.cash
        initial_player_cash = self.player.cash

        loan = self.company.take_loan(500, self.player, 0.05, 1)

        self.assertEqual(self.company.cash, initial_cash + 500)
        self.assertEqual(self.player.cash, initial_player_cash - 500)
        self.assertEqual(len(self.company.loans), 1)
        self.assertEqual(loan.balance, 500)

    def test_repay_loan_decreases_company_cash(self):
        """Repaying a loan decreases company cash."""
        loan = self.company.take_loan(500, self.player, 0.05, 1)
        self.company.cash = 700  # Give company enough cash to repay
        initial_player_cash = self.player.cash

        actual_payment = self.company.repay_loan(loan, 300)

        self.assertEqual(actual_payment, 300)
        self.assertEqual(self.company.cash, 400)  # 700 - 300
        self.assertEqual(self.player.cash, initial_player_cash + 300)
        self.assertEqual(loan.balance, 200)
        self.assertEqual(len(self.company.loans), 1)  # Still outstanding

    def test_repay_loan_fully_removes_loan(self):
        """Fully repaying a loan removes it from the list."""
        loan = self.company.take_loan(500, self.player, 0.05, 1)
        self.company.cash = 600

        actual_payment = self.company.repay_loan(loan, 500)

        self.assertEqual(actual_payment, 500)
        self.assertEqual(len(self.company.loans), 0)  # Loan removed

    def test_accrue_loan_interest_on_multiple_loans(self):
        """Interest accrues correctly on multiple loans."""
        loan1 = self.company.take_loan(1000, self.player, 0.10, 1)
        loan2 = self.company.take_loan(500, self.player, 0.05, 2)

        self.company.accrue_loan_interest()

        self.assertEqual(loan1.balance, 1100)  # 1000 * 1.10
        self.assertEqual(loan2.balance, 525)   # 500 * 1.05

    def test_total_debt_calculation(self):
        """Total debt is calculated correctly across multiple loans."""
        self.company.take_loan(1000, self.player, 0.05, 1)
        self.company.take_loan(500, self.player, 0.05, 2)

        total = self.company.total_debt()
        self.assertEqual(total, 1500)

    def test_can_service_debt_with_sufficient_cash(self):
        """Company with sufficient cash can service debt."""
        self.company.take_loan(1000, self.player, 0.05, 1)
        self.company.cash = 200  # 10% of 1000 is 100, so 200 is enough

        self.assertTrue(self.company.can_service_debt())

    def test_cannot_service_debt_with_insufficient_cash(self):
        """Company with insufficient cash cannot service debt."""
        self.company.take_loan(1000, self.player, 0.05, 1)
        self.company.cash = 50  # 10% of 1000 is 100, so 50 is not enough

        self.assertFalse(self.company.can_service_debt())

    def test_multiple_loans_lifecycle(self):
        """Test complete lifecycle with multiple loans."""
        # Take two loans
        loan1 = self.company.take_loan(1000, self.player, 0.10, 1)
        loan2 = self.company.take_loan(500, self.player, 0.05, 2)

        self.assertEqual(self.company.total_debt(), 1500)

        # Accrue interest
        self.company.accrue_loan_interest()
        self.assertEqual(self.company.total_debt(), 1625)  # 1100 + 525

        # Repay part of loan1
        self.company.cash = 1000
        self.company.repay_loan(loan1, 600)
        self.assertEqual(loan1.balance, 500)  # 1100 - 600
        self.assertEqual(self.company.total_debt(), 1025)  # 500 + 525

        # Repay loan2 completely
        self.company.repay_loan(loan2, 525)
        self.assertEqual(len(self.company.loans), 1)  # Only loan1 remains
        self.assertEqual(self.company.total_debt(), 500)

    def test_cannot_repay_non_existent_loan(self):
        """Repaying a loan not in the company's list returns 0."""
        other_loan = Loan(
            id="other",
            principal=100,
            balance=100,
            interest_rate=0.05,
            lender=self.player,
            round_taken=1
        )

        self.company.cash = 200
        actual_payment = self.company.repay_loan(other_loan, 100)

        self.assertEqual(actual_payment, 0)
        self.assertEqual(self.company.cash, 200)  # Cash unchanged


if __name__ == '__main__':
    unittest.main()
