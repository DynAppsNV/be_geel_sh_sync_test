# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.addons.pos_enterprise.tests.test_frontend import TestPreparationDisplayHttpCommon
from odoo.addons.pos_urban_piper.tests.test_frontend import TestPosUrbanPiperCommon


class TestUrbanPiperPreparationDisplayEnhancements(TestPosUrbanPiperCommon, TestPreparationDisplayHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pdis.pos_config_ids = [Command.set(cls.urban_piper_config.ids)]

    def test_preparation_display_future_delivery_order(self):
        self.urban_piper_config.open_ui()
        order = self._create_urbanpiper_test_order(self.product_1)
        order.delivery_datetime = datetime.now() + timedelta(minutes=10)

        self.start_pos_tour('test_pos_urbanpiper_future_delivery_order', pos_config=self.urban_piper_config)
        self.env['pos.prep.order'].process_order(order.ids)
        self.start_pdis_tour('test_preparation_display_future_delivery_order', login='pos_admin')
        prep_order = self.env['pos.prep.order'].search([('pos_order_id', '=', order.id)])
        self.assertEqual(len(prep_order), 1)
        self.assertEqual(bool(prep_order.delivery_datetime), True)
