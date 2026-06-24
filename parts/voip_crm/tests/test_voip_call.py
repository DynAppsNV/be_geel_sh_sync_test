from odoo.tests import users

from odoo.addons.crm.tests.common import TestCrmCommon


class TestVoipCall(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Partner",
            "phone": "110",
        })
        cls.lead_1 = cls.env["crm.lead"].create({
            "name": "Test Opportunity",
            "type": "opportunity",
            "partner_id": cls.partner.id,
            "user_id": cls.user_sales_salesman.id,
            "probability": 40,
        })
        cls.lead_2 = cls.env["crm.lead"].create({
            "name": "Test Lead",
            "type": "lead",
            "partner_id": cls.partner.id,
            "user_id": cls.user_sales_manager.id,
        })
        cls.call_1 = cls.env["voip.call"].create({
            "partner_id": cls.partner.id,
            "phone_number": "110",
            "user_id": cls.user_sales_salesman.id,
        })
        cls.call_2 = cls.env["voip.call"].create({
            "partner_id": cls.partner.id,
            "phone_number": "110",
            "user_id": cls.user_sales_manager.id,
        })

    @users("user_sales_salesman")
    def test_voip_call_opportunity_count_salesman(self):
        partner = self.partner.with_env(self.env)
        call = self.call_1.with_env(self.env)
        self.assertEqual(call.opportunity_count, partner.opportunity_count,
                         "The opportunity counts on the call should match those on the partner.")

    @users("user_sales_manager")
    def test_voip_call_opportunity_count_manager(self):
        partner = self.partner.with_env(self.env)
        call = self.call_2.with_env(self.env)
        self.assertEqual(call.opportunity_count, partner.opportunity_count,
                         "The opportunity counts on the call should match those on the partner.")
