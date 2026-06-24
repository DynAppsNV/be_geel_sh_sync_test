from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPaymentReceiptEmail(TransactionCase):
    """Test automatic payment receipt email sending."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Minimum accounting setup for a test DB without a chart of accounts.
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Test Revenue",
                "code": "400000TEST",
                "account_type": "income",
            }
        )
        cls.receivable_account = cls.env["account.account"].create(
            {
                "name": "Test Receivable",
                "code": "130000TEST",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        # Required by _get_outstanding_account() when no chart template is installed.
        cls.outstanding_account = cls.env["account.account"].create(
            {
                "name": "Test Outstanding",
                "code": "100000TEST",
                "account_type": "asset_current",
            }
        )
        cls.env.company.write({"transfer_account_id": cls.outstanding_account.id})

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Customer",
                "email": "test.customer@example.com",
                "property_account_receivable_id": cls.receivable_account.id,
            }
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 100.0,
            }
        )

        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create(
                {"name": "Customer Invoices", "type": "sale", "code": "INV"}
            )

        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create(
                {"name": "Bank", "type": "bank", "code": "BNK"}
            )

    def _make_invoice(self, quantity=1, price_unit=100.0):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": "2024-01-01",
                "journal_id": self.journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": quantity,
                            "price_unit": price_unit,
                            "account_id": self.income_account.id,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )

    def _register_payment(self, invoice):
        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        return (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move.line",
                active_ids=receivable_lines.ids,
            )
            .create(
                {
                    "amount": invoice.amount_total,
                    "payment_date": "2024-01-01",
                    "journal_id": self.bank_journal.id,
                }
            )
        )

    def test_payment_receipt_email_sent_on_payment_creation(self):
        """Email is sent when payment is created via the register wizard for an invoice."""
        invoice = self._make_invoice()
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

        payment_register = self._register_payment(invoice)

        template = self.env.ref("account.mail_template_data_payment_receipt")
        with patch.object(type(template), "send_mail") as mock_send_mail:
            action = payment_register.action_create_payments()

            if isinstance(action, dict) and action.get("res_model") == "account.payment":
                if "res_id" in action:
                    payment_id = action["res_id"]
                else:
                    payment_id = action["domain"][0][2][0]
            else:
                payment_id = (
                    self.env["account.payment"]
                    .search([("partner_id", "=", self.partner.id)], limit=1)
                    .id
                )

            payment = self.env["account.payment"].browse(payment_id)
            self.assertTrue(payment.exists())
            self.assertIn(payment.state, ("in_process", "paid"))
            self.assertEqual(payment.amount, 100.0)
            self.assertEqual(payment.partner_id, self.partner)
            self.assertIn(invoice, payment.invoice_ids)

            mock_send_mail.assert_called_once_with(payment.id, force_send=True)

    def test_payment_receipt_no_email_if_no_invoices(self):
        """No email is sent when a standalone payment (no linked invoices) is posted."""
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner.id,
                "amount": 50.0,
                "journal_id": self.bank_journal.id,
                "date": "2024-01-01",
            }
        )

        template = self.env.ref("account.mail_template_data_payment_receipt")
        with patch.object(type(template), "send_mail") as mock_send_mail:
            payment.action_post()
            mock_send_mail.assert_not_called()

    def test_payment_receipt_template_uses_invoice_ids(self):
        """Payment receipt report renders and includes the invoice reference."""
        invoice = self._make_invoice(quantity=2, price_unit=50.0)
        invoice.action_post()

        payment_register = self._register_payment(invoice)
        action = payment_register.action_create_payments()

        if isinstance(action, dict) and "res_id" in action:
            payment = self.env["account.payment"].browse(action["res_id"])
        else:
            payment = self.env["account.payment"].search(
                [("partner_id", "=", self.partner.id)], limit=1
            )

        rendered = self.env["ir.qweb"]._render(
            "account.report_payment_receipt_document", {"o": payment}
        )

        self.assertIn(invoice.name, rendered)
        self.assertIn("100.00", rendered)
