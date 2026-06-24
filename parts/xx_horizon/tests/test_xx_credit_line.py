import json
from datetime import date

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCreditLine(TransactionCase):
    def setUp(self):
        super().setUp()

        self.payment_term = self.env["account.payment.term"].create(
            {
                "name": "30 Days",
            }
        )

        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Customer",
                "property_payment_term_id": self.payment_term.id,
            }
        )

        self.credit_type = self.env["xx.credit.line.type"].create(
            {
                "description": "Standard",
                "code": "STD",
            }
        )

        self.currency = self.env.ref("base.USD")

    def test_create_creates_sync_record(self):
        form = Form(self.env["xx.credit.line"])
        form.customer_id = self.partner
        form.credit_line_type_id = self.credit_type
        form.amount = 5000
        form.expiration_date = date(2026, 2, 1)
        form.date = date(2026, 1, 1)
        form.currency_id = self.currency

        credit_line = form.save()

        sync_record = self.env["xx.sync.record"].search(
            [("model_name", "=", "xx.credit.line"), ("method", "=", "POST")],
            limit=1,
        )

        self.assertTrue(sync_record)

        payload = json.loads(sync_record.content)[0]

        self.assertEqual(payload["Code"], credit_line.id)
        self.assertEqual(payload["Contact_ID"], self.partner.id)
        self.assertEqual(payload["Type"], "STD")
        self.assertEqual(payload["limit"], 5000)
        self.assertFalse(payload["Blocked"])
        self.assertEqual(sync_record.synced, False)

    def test_write_relevant_field_triggers_put(self):
        credit_line = self.env["xx.credit.line"].create(
            {
                "customer_id": self.partner.id,
                "credit_line_type_id": self.credit_type.id,
                "amount": 1000,
                "date": date(2026, 1, 1),
                "currency_id": self.currency.id,
            }
        )

        self.env["xx.sync.record"].search([]).unlink()

        credit_line.write({"amount": 2000})

        sync_record = self.env["xx.sync.record"].search(
            [("method", "=", "PUT")],
            limit=1,
        )

        self.assertTrue(sync_record)

        payload = json.loads(sync_record.content)[0]
        self.assertEqual(payload["limit"], 2000)

    def test_write_irrelevant_field_does_not_trigger(self):
        credit_line = self.env["xx.credit.line"].create(
            {
                "customer_id": self.partner.id,
                "credit_line_type_id": self.credit_type.id,
                "amount": 1000,
                "date": date(2026, 1, 1),
                "currency_id": self.currency.id,
            }
        )

        self.env["xx.sync.record"].search([]).unlink()

        credit_line.write({"our_reference": "Updated Reference"})

        sync_records = self.env["xx.sync.record"].search([])
        self.assertFalse(sync_records)

    def test_unlink_triggers_delete_sync(self):
        credit_line = self.env["xx.credit.line"].create(
            {
                "customer_id": self.partner.id,
                "credit_line_type_id": self.credit_type.id,
                "amount": 1000,
                "date": date(2026, 1, 1),
                "currency_id": self.currency.id,
            }
        )

        self.env["xx.sync.record"].search([]).unlink()

        credit_line.unlink()

        sync_record = self.env["xx.sync.record"].search(
            [("method", "=", "DELETE")],
            limit=1,
        )

        self.assertTrue(sync_record)
