from odoo import Command
from odoo.tests import users

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


class TestVoipCall(TestSubscriptionCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_sales_salesman = cls.env["res.users"].create({
            "login": "user_sales_salesman",
            "name": "user_sales_salesman",
            "email": "user_sales_salesman@example.com",
            "group_ids": [Command.link(cls.env.ref("sales_team.group_sale_salesman").id)]
        })
        cls.user_sales_manager = cls.env["res.users"].create({
            "login": "user_sales_manager",
            "name": "user_sales_manager",
            "email": "user_sales_manager@example.com",
            "group_ids": [Command.link(cls.env.ref("sales_team.group_sale_manager").id)]
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Partner",
            "phone": "110",
        })
        cls.subscription_1 = cls.env['sale.order'].create({
            'name': 'Test Subscription 1',
            'is_subscription': True,
            'state': 'sale',
            'subscription_state': '3_progress',
            'plan_id': cls.plan_month.id,
            'partner_id': cls.partner.id,
            'user_id': cls.user_sales_salesman.id,
            'order_line': [Command.create({
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'tax_ids': [Command.clear()],
            })],
        })
        cls.subscription_2 = cls.env['sale.order'].create({
            'name': 'Test Subscription 2',
            'is_subscription': True,
            'state': 'sale',
            'subscription_state': '6_churn',
            'plan_id': cls.plan_month.id,
            'partner_id': cls.partner.id,
            'user_id': cls.user_sales_manager.id,
            'order_line': [Command.create({
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'tax_ids': [Command.clear()],
            })],
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
    def test_voip_call_subscription_count_user(self):
        partner = self.partner.with_env(self.env)
        call = self.call_1.with_env(self.env)
        self.assertEqual(partner.subscription_count, call.subscription_count,
                         "The subscription counts on the call should match those on the partner.")

    @users("user_sales_manager")
    def test_voip_call_subscription_count_manager(self):
        partner = self.partner.with_env(self.env)
        call = self.call_2.with_env(self.env)
        self.assertEqual(partner.subscription_count, call.subscription_count,
                         "The subscription counts on the call should match those on the partner.")
