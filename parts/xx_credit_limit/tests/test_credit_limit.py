from datetime import datetime

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load the res.partner model
        cls.PartnerModel = cls.env["res.partner"]

    def test_res_partner_model(self):
        with self.assertRaises(ValidationError, msg="Negative credit limit is not allowed"):
            self.PartnerModel.create(
                {"name": "Test Partner", "credit_limit": -100.0}
            )  # Should raise a ValidationError

    def test_res_partner_inherited_model(self):
        partner = self.PartnerModel.create(
            {"name": "Test Partner Inherited", "credit_limit": 100.0}
        )
        self.assertEqual(partner.credit_limit, 100.0)


@tagged("post_install", "-at_install")
class TestCreditLine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.CreditLineModel = cls.env["xx.credit.line"]
        cls.CreditLineTypeModel = cls.env["xx.credit.line.type"]
        cls.PartnerModel = cls.env["res.partner"]

    def test_credit_line_model(self):
        # Create a sale order with valid values
        partner = self.PartnerModel.create({"name": "Test Partner"})
        credit_line_type = self.CreditLineTypeModel.create(
            {"code": "TEST01", "description": "Test Type 01"}
        )

        line1 = self.CreditLineModel.create(
            {
                "customer_id": partner.id,
                "credit_line_type_id": credit_line_type.id,
                "date": datetime.today(),
                "amount": 1000,
                "currency_id": 125,
            }
        )

        line2 = self.CreditLineModel.create(
            {
                "customer_id": partner.id,
                "credit_line_type_id": credit_line_type.id,
                "date": datetime.fromisocalendar(2025, 1, 1),
                "expiration_date": datetime.fromisocalendar(2025, 2, 1),
                "amount": 1000,
                "currency_id": 125,
            }
        )

        total_credit = partner.calculate_available_credit()
        self.assertEqual(total_credit, 1000)

        line1.unlink()
        self.assertEqual(total_credit, 1000)

        line2.unlink()
        credit_line_type.unlink()
