from datetime import date, timedelta

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentTerms(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.currency = self.company.currency_id
        self.partner = self.env["res.partner"].create({"name": "Vendor"})

        self.account_payable = self.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
            ],
            limit=1,
        )

        self.payment_term = self.env["account.payment.term"].create(
            {
                "name": "Early discount",
                "early_discount": True,
                "discount_percentage": 2.0,
                "discount_days": 10,
            }
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _create_bill(self, invoice_date):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": invoice_date,
                "invoice_payment_term_id": self.payment_term.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Expense",
                            "account_id": self.env["account.account"].search([], limit=1).id,
                            "quantity": 1,
                            "price_unit": 100.0,
                            "partner_id": self.partner.id,
                            "currency_id": self.currency.id,
                        },
                    ),
                ],
            }
        )

        total_debit = sum(line.debit for line in bill.line_ids)
        total_credit = sum(line.credit for line in bill.line_ids)
        assert total_debit == total_credit, f"Debit {total_debit} != Credit {total_credit}"

        bill.action_post()
        assert bill.amount_residual > 0
        return bill

    def _create_wizard(self, bills, context=None):
        ctx_kwargs = dict(context or {})
        ctx_kwargs.setdefault("active_model", "account.move")
        ctx_kwargs.setdefault("active_ids", bills.ids if hasattr(bills, "ids") else [bills.id])
        return (
            self.env["account.payment.register"]
            .with_context(**ctx_kwargs)
            .create(
                {
                    "partner_id": self.partner.id,
                    "line_ids": [(6, 0, bills.mapped("line_ids").ids)],
                }
            )
        )

    def _create_line(self, move, context=None):
        ctx_kwargs = dict(context or {})
        return (
            self.env["xx.account.payment.register.line"]
            .with_context(**ctx_kwargs)
            .create(
                {
                    "move_id": move.id,
                    "currency_id": self.currency.id,
                }
            )
        )

    # =========================================================
    # Account Payment Register Line Tests
    # =========================================================
    @freeze_time("2026-01-27")
    def test_discount_active(self):
        bill = self._create_bill(date(2026, 1, 20))
        line = self._create_line(bill)

        self.assertFalse(line.discount_expired)
        self.assertEqual(line.discount_status, "active")
        self.assertEqual(line.discount_date, bill.invoice_date + timedelta(days=10))

    @freeze_time("2026-01-27")
    def test_discount_expired(self):
        bill = self._create_bill(date(2026, 1, 10))
        line = self._create_line(bill)

        self.assertTrue(line.discount_expired)
        self.assertEqual(line.discount_status, "expired")

    @freeze_time("2026-01-27")
    def test_expired_without_early_discount(self):
        bill = self._create_bill(date(2026, 1, 10))
        line = self._create_line(bill)

        line.early_discount = False
        self.assertTrue(line.discount_expired)
        self.assertEqual(line.discount_status, "expired")

    @freeze_time("2026-01-27")
    def test_expired_force_apply_discount(self):
        bill = self._create_bill(date(2026, 1, 10))
        ctx = {"force_apply_writeoff": {bill.id: True}}
        line = self._create_line(bill, context=ctx)

        line.early_discount = True
        self.assertTrue(line.discount_expired)
        self.assertEqual(line.discount_status, "applied")

    @freeze_time("2026-01-27")
    def test_no_discount_payment_term(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": date(2026, 1, 27),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Line",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": self.account_payable.id,
                        },
                    )
                ],
            }
        )
        line = self._create_line(bill)

        self.assertFalse(line.discount_expired)
        self.assertFalse(line.discount_date)
        self.assertEqual(line.discount_status, "")

    # =========================================================
    # Account Payment Register Wizard Tests
    # =========================================================
    @freeze_time("2026-01-27")
    def test_default_get_populates_bill_lines(self):
        bill = self._create_bill(date(2026, 1, 20))
        wiz = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=[bill.id],
            )
        ).save()
        values = wiz.default_get(["bill_line_ids"])
        self.assertTrue(values.get("bill_line_ids"))

    @freeze_time("2026-01-27")
    def test_default_get_force_apply_context(self):
        bill = self._create_bill(date(2026, 1, 20))
        wiz = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=[bill.id],
                force_apply_writeoff={bill.id: True},
            )
        ).save()
        values = wiz.default_get(["bill_line_ids"])
        line_vals = values["bill_line_ids"][0][2]
        self.assertTrue(line_vals["early_discount"])

    @freeze_time("2026-01-27")
    def test_has_early_discount_expired_unchecked(self):
        bill = self._create_bill(date(2026, 1, 10))
        wiz = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=bill.ids,
            )
        ).save()
        self.assertTrue(wiz.has_early_discount)

    @freeze_time("2026-01-27")
    def test_has_early_discount_checked_not_applied(self):
        bill = self._create_bill(date(2026, 1, 10))

        with Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=bill.ids,
            )
        ) as wiz_form:
            with wiz_form.bill_line_ids.edit(0) as line_form:
                line_form.early_discount = True

        wiz = wiz_form.save()
        self.assertTrue(wiz.has_early_discount)

    @freeze_time("2026-01-27")
    def test_has_early_discount_active(self):
        bill = self._create_bill(date(2026, 1, 20))
        wiz = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=bill.ids,
            )
        ).save()
        self.assertFalse(wiz.has_early_discount)

    @freeze_time("2026-01-27")
    def test_force_apply_writeoff_context(self):
        bill = self._create_bill(date(2026, 1, 10))

        with Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=bill.ids,
            )
        ) as wiz_form:
            with wiz_form.bill_line_ids.edit(0) as line_form:
                line_form.early_discount = True

        wiz = wiz_form.save()
        action = wiz.force_apply_writeoff()
        self.assertIn("force_apply_writeoff", action["context"])
        self.assertTrue(action["context"]["force_apply_writeoff"][bill.id])

    @freeze_time("2026-01-27")
    def test_action_create_payments_raises_if_not_applied(self):
        bill = self._create_bill(date(2026, 1, 10))

        with Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=bill.ids,
            )
        ) as wiz_form:
            with wiz_form.bill_line_ids.edit(0) as line_form:
                line_form.early_discount = True

        wiz = wiz_form.save()
        wiz.bill_line_ids[0].early_discount = True
        with self.assertRaises(UserError):
            wiz.action_create_payments()

    @freeze_time("2026-01-27")
    def test_action_create_payments_ok_when_applied(self):
        bill = self._create_bill(date(2026, 1, 10))

        with Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=bill.ids,
                force_apply_writeoff={bill.id: True},
            )
        ) as wiz_form:
            wiz = wiz_form.save()
            wiz.action_create_payments()
