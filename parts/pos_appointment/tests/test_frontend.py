# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.pos_appointment.tests.test_pos_appointment_flow import CommonPosAppointmentTest
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestFrontend(CommonPosAppointmentTest, TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.write({
            'module_pos_appointment': True,
            'appointment_type_id': cls.reservation_appointment.id,
        })

    def test_appointment_kanban_view_date_filter(self):
        self.start_pos_tour('test_appointment_kanban_view_date_filter')
