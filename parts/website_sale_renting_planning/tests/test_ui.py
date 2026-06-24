# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time
from functools import wraps
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale_renting_planning.controllers.main import WebsiteSalePlanningRenting
from odoo.addons.website_sale_renting_planning.tests.test_website_sale_renting_planning import (
    TestWebsiteSaleRentingPlanning,
)


@tagged("-at_install", "post_install")
class TestUi(TestWebsiteSaleRentingPlanning):
    @freeze_time("2999-03-11 08:00:00")
    def test_website_sale_renting_planning_max_qty(self):
        other_employee = self.env["hr.employee"].create(
            {"name": "Other employee", "contract_date_start": date.today()}
        )
        self.planning_role.resource_ids = self.employee.resource_id + other_employee.resource_id

        og_renting_product_availabilities = (
            WebsiteSalePlanningRenting.renting_product_availabilities
        )

        def _patched_renting_product_availabilities(*args, **kwargs):
            kwargs["min_date"] = "2999-03-11 08:00:00"
            kwargs["max_date"] = "2999-03-22 10:00:00"
            return og_renting_product_availabilities(*args, **kwargs)

        with patch(
            "odoo.addons.website_sale_renting_planning.controllers.main.WebsiteSalePlanningRenting.renting_product_availabilities",
            wraps(og_renting_product_availabilities)(_patched_renting_product_availabilities),
        ):
            self.start_tour(
                "/shop?search=Product+Renting+Planning",
                "website_sale_renting_planning_max_qty",
                login="admin",
            )

    def test_website_sale_renting_planning_buy_product(self):
        """ Test the UI from the product page """
        payment_demo = self.env['ir.module.module']._get('payment_demo')
        if payment_demo.state != 'installed':
            self.skipTest("payment_demo module is not installed")
        self.employee.resource_id.calendar_id = False
        self.env['planning.slot'].create({
            'resource_id': self.employee.resource_id.id,
            'role_id': self.planning_role.id,
            'start_datetime': self.start_date,
            'end_datetime': self.end_date,
        })
        with freeze_time(self.start_date.strftime(self.date_format)):
            self.start_tour("/shop", "website_sale_renting_planning_buy_product")
        sale_order = self._get_sale_order(confirmed=True)
        self.assertTrue(sale_order, "No sale order was created from ecommerce.")
        self.assertEqual(sale_order.state, 'sale', "The order should be in 'sale' state.")
        planning_slot = sale_order.order_line.planning_slot_ids
        self.assertTrue(planning_slot, "There should be planning slots assigned for this product rental.")
        self.assertEqual(len(planning_slot), 1, "There should be exactly 1 slot allocated to the rental Period.")
