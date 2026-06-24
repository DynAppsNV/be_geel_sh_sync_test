from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.float_utils import float_round


@tagged("post_install", "-at_install")
class TestAnalyticDistribution(TransactionCase):
    def test_view_arch_loads(self):
        """Test that the analytic distribution view customisation renders without errors."""
        self.env.ref("xx_analytic_distribution.xx_account_move_form_analytic_distribution")


@tagged("post_install", "-at_install")
class TestAnalyticDistributionRounding(TransactionCase):
    """Verify that percentage precision determines round-trip accuracy of entered amounts.

    With 4-decimal percentages, applying the percentage back to the same balance recovers
    the original 2-decimal amount without rounding error.  These tests call
    _prepare_analytic_distribution_line directly — the same method used by
    _create_analytic_lines at posting time — to verify the rounding behaviour in isolation.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company

        cls.plan = cls.env["account.analytic.plan"].create({"name": "Test Plan"})
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {"name": "Test Account", "plan_id": cls.plan.id}
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Test Expense",
                "code": "620001XX",
                "account_type": "expense",
                "company_ids": [company.id],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Vendor"})

    def _make_expense_line(self, price):
        """Create a draft vendor bill and return its expense line."""
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test service",
                            "account_id": self.expense_account.id,
                            "price_unit": price,
                            "quantity": 1,
                        }
                    )
                ],
            }
        )
        return bill.line_ids.filtered(lambda ln: ln.account_id == self.expense_account)

    def _compute_amount(self, line, percentage):
        """Run _prepare_analytic_distribution_line and apply currency rounding."""
        acc_key = str(self.analytic_account.id)
        vals = line._prepare_analytic_distribution_line(percentage, acc_key, {})
        return line.company_currency_id.round(vals["amount"])

    def test_rounding_error_with_two_decimal_percentage(self):
        """2-decimal % loses precision: 3000 × 3.33% = 99.90, not 100.00.

        Documents the behaviour at the Odoo default of 2 decimal places, where the
        percentage cannot represent the amount exactly, producing a visible rounding error.
        """
        line = self._make_expense_line(3000.0)
        amount = self._compute_amount(line, 3.33)
        # 3000 × 3.33 / 100 = 99.9 — clearly off by 0.10
        self.assertAlmostEqual(abs(amount), 99.90, places=2)
        self.assertNotAlmostEqual(abs(amount), 100.00, places=1)

    def test_no_rounding_error_with_four_decimal_percentage(self):
        """4-decimal % recovers the exact amount: 3000 × 3.3333% = 99.999 → 100.00.

        Documents the post-fix behaviour with 4-decimal-place percentages, which after
        currency rounding gives back the originally entered amount.
        """
        line = self._make_expense_line(3000.0)
        amount = self._compute_amount(line, 3.3333)
        # 3000 × 3.3333 / 100 = 99.999 → rounds to 100.00
        self.assertAlmostEqual(abs(amount), 100.00, places=2)

    def test_no_rounding_error_terminating_fraction(self):
        """Terminating fractions are exact at any precision level."""
        line = self._make_expense_line(1000.0)
        amount = self._compute_amount(line, 10.00)
        self.assertAlmostEqual(abs(amount), 100.00, places=2)


@tagged("post_install", "-at_install")
class TestAnalyticDistributionPrecision(TransactionCase):
    """The widget can compute high-precision percentages, but the server rounds the
    stored analytic_distribution to the "Percentage Analytic" decimal precision in
    analytic.mixin._sanitize_values() on every create/write. With the Odoo default
    of 2 the extra decimals are silently truncated, so the amount drifts on reload
    (e.g. 9.99 -> 9.96 on a 1200 balance). This module bumps that precision to 6
    (RA-111), which keeps the amount cent-exact for any realistic balance.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.plan = cls.env["account.analytic.plan"].create({"name": "Precision Plan"})
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {"name": "Precision Account", "plan_id": cls.plan.id}
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Precision Expense",
                "code": "620002XX",
                "account_type": "expense",
                "company_ids": [company.id],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Precision Vendor"})

    def test_percentage_analytic_precision_is_six(self):
        """The module raises "Percentage Analytic" precision from the default 2 to 6."""
        digits = self.env["decimal.precision"].precision_get("Percentage Analytic")
        self.assertEqual(digits, 6)

    def _line_with_distribution(self, distribution):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Service",
                            "account_id": self.expense_account.id,
                            "price_unit": 1200.0,
                            "quantity": 1,
                            "analytic_distribution": distribution,
                        }
                    )
                ],
            }
        )
        return bill.line_ids.filtered(lambda ln: ln.account_id == self.expense_account)

    def test_six_decimal_percentage_is_preserved(self):
        """A 6-decimal percentage survives the server-side sanitisation."""
        acc_key = str(self.analytic_account.id)
        line = self._line_with_distribution({acc_key: 0.832541})
        self.assertEqual(line.analytic_distribution[acc_key], 0.832541)

    def test_seventh_decimal_is_rounded_to_six(self):
        """Beyond 6 decimals the value is still rounded — 6 is the configured limit."""
        acc_key = str(self.analytic_account.id)
        line = self._line_with_distribution({acc_key: 0.8325416})
        self.assertEqual(line.analytic_distribution[acc_key], 0.832542)


@tagged("post_install", "-at_install")
class TestAnalyticDistributionWidgetRoundTrip(TransactionCase):
    """Quantify the RA-111 round-trip drift of the analytic_distribution widget.

    The widget stores distributions as *percentages* rounded to the "Percentage
    Analytic" decimal precision, but the user edits *amounts*. Tabbing out of an
    amount field runs an amount -> percentage -> amount round-trip; when the
    percentage precision is too coarse to represent the entered amount, the amount
    snaps to the nearest representable value and the leftover is pushed into an
    auto-created remainder line.

    These tests do not touch the DB — they replicate the widget arithmetic exactly
    (analytic_distribution.js: ``lineChanged``, ``recordProps`` and ``addLine``) so
    we can measure the drift in cents and the size of the spurious remainder line,
    and so we can quantify the effect of any change to the configured precision.

    The ticket scenario: a journal item of €14,402.67 split three ways. Items 1 and
    2 are fixed; item 3 (€5,761.06 / 40%) is the one being tabbed out of.
    """

    # Ticket figures (signs dropped — the widget works on magnitudes).
    TICKET_BALANCE = 14402.67
    TICKET_AMOUNTS = (3333.33, 5308.28, 5761.06)

    @staticmethod
    def _widget_round_trip(balance, amounts, analytic_precision):
        """Replicate the widget's amount/percentage/amount round-trip.

        Mirrors ``analytic_distribution.js``:

        * ``lineChanged`` stores the line *fraction* (percentage / 100) as
          ``roundDecimals(amount / balance, precision + 2)`` — i.e. the fraction is
          rounded to ``precision + 2`` digits, which is the percentage rounded to
          ``precision`` digits.
        * ``recordProps`` shows the amount back as ``balance * fraction`` (the
          monetary widget then rounds it to the currency's 2 digits).
        * ``addLine`` seeds an auto-created line with
          ``roundDecimals(1 - sum(fractions), precision + 2)``.

        ``float_round`` uses HALF-UP, the same tie-break as the JS ``roundDecimals``.
        Returns ``(fractions, displayed_amounts, remainder_fraction, remainder_amount)``.
        """
        digits = analytic_precision + 2
        fractions = [float_round(a / balance, precision_digits=digits) for a in amounts]
        displayed = [float_round(balance * f, precision_digits=2) for f in fractions]
        remainder = float_round(1 - sum(fractions), precision_digits=digits)
        remainder_amount = float_round(balance * remainder, precision_digits=2)
        return fractions, displayed, remainder, remainder_amount

    def test_round_trip_drifts_at_precision_four(self):
        """RA-111 (current behaviour): 4-decimal % cannot represent €5,761.06.

        Tabbing out drifts the amount to €5,761.05 (one cent low) and the leftover
        0.0001% spawns a spurious €0.01 line. The amount resolution at 4 decimals is
        0.0001% × €14,402.67 ≈ €0.0144 > €0.01, so some cent amounts are unreachable.
        """
        fractions, displayed, remainder, remainder_amount = self._widget_round_trip(
            self.TICKET_BALANCE, self.TICKET_AMOUNTS, analytic_precision=4
        )
        # Item 3 was entered as 5761.06 but snaps down a cent.
        self.assertEqual(displayed[2], 5761.05)
        self.assertEqual(round(fractions[2] * 100, 4), 39.9999)
        # A spurious remainder line of 0.0001% / €0.01 is created.
        self.assertEqual(round(remainder * 100, 4), 0.0001)
        self.assertEqual(remainder_amount, 0.01)

    def test_round_trip_exact_at_precision_six(self):
        """RA-111 (proposed fix): 6-decimal % represents €5,761.06 exactly.

        The same entry round-trips to €5,761.06 and the fractions sum to 1.0, so no
        remainder line is created. At 6 decimals the resolution is
        0.000001% × €14,402.67 ≈ €0.00014, far below a cent, for any realistic balance.
        """
        fractions, displayed, remainder, remainder_amount = self._widget_round_trip(
            self.TICKET_BALANCE, self.TICKET_AMOUNTS, analytic_precision=6
        )
        # Item 3 keeps the entered amount.
        self.assertEqual(displayed[2], 5761.06)
        # No drift on items 1 and 2 either.
        self.assertEqual(displayed[0], 3333.33)
        self.assertEqual(displayed[1], 5308.28)
        # No spurious remainder line.
        self.assertEqual(remainder, 0.0)
        self.assertEqual(remainder_amount, 0.0)

    def test_amount_resolution_threshold(self):
        """Document the balance above which 4-decimal % can no longer hit every cent.

        The smallest representable amount step is ``balance × 10**-(precision + 2)``.
        Cent-exact round-trips are only guaranteed while that step stays at/below
        €0.01, i.e. balance ≤ €10,000 at precision 4 but ≤ €1,000,000 at precision 6.
        The ticket's €14,402.67 sits in the gap, which is why it only breaks at 4.
        """
        step_at_4 = self.TICKET_BALANCE * 10 ** -(4 + 2)
        step_at_6 = self.TICKET_BALANCE * 10 ** -(6 + 2)
        self.assertGreater(step_at_4, 0.01)  # coarser than a cent -> drift possible
        self.assertLess(step_at_6, 0.01)  # finer than a cent -> exact
