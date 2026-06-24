from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPoSAvatax(TestPointOfSaleHttpCommon):
    def test_pos_avatax_flow(self):
        self.main_pos_config.module_pos_avatax = True
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_pos_avatax_flow', login="accountman")

    def test_pos_fiscal_position_without_pos_avatax(self):
        """ Test that fiscal positions using AvaTax are ignored when AvaTax is not activated in POS """
        existing_fp = self.env['account.fiscal.position'].search([('company_id', '=', self.env.company.id)])
        existing_fp.active = False
        self.env['account.fiscal.position'].create({
            'name': "AvaTax FP",
            'is_avatax': True,
            'auto_apply': True,
            'country_id': self.env.ref('base.us').id,
        })
        default_fp = self.env['account.fiscal.position'].create({
            'name': "Default FP",
            'is_avatax': False,
            'auto_apply': False,
        })
        self.env['res.partner'].create({
            'name': 'A US Partner',
            'street': '1 Infinite Loop',
            'city': 'Cupertino',
            'zip': '95014-2083',
            'state_id': self.env.ref('base.state_us_13').id,
            'country_id': self.env.ref('base.us').id,
        })
        self.main_pos_config.module_pos_avatax = False
        self.main_pos_config.default_fiscal_position_id = default_fp
        self.main_pos_config.fiscal_position_ids = default_fp
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_pos_fiscal_position_without_pos_avatax', login="pos_user")
