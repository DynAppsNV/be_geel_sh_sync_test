# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import uuid

import odoo.tests
from odoo import Command
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.point_of_sale.tests.common import archive_products
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient
from odoo.addons.pos_urban_piper.controllers.main import PosUrbanPiperController
from unittest.mock import patch


@odoo.tests.tagged('post_install', '-at_install')
class TestPosUrbanPiperCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)
        cls.env['product.product'].search([
            ('id', 'in', [
                cls.env.ref('pos_urban_piper.product_packaging_charges').id,
                cls.env.ref('pos_urban_piper.product_delivery_charges').id,
                cls.env.ref('pos_urban_piper.product_other_charges').id,
            ])
        ]).product_tmpl_id.write({
            'active': True,
        })
        cls.env['ir.config_parameter'].set_param('pos_urban_piper.urbanpiper_username', 'demo')
        cls.env['ir.config_parameter'].set_param('pos_urban_piper.urbanpiper_apikey', 'demo')
        cls.urban_piper_config = cls.env['pos.config'].create({
            'name': 'Urban Piper',
            'module_pos_urban_piper': True,
            'urbanpiper_delivery_provider_ids': [Command.set([cls.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id])]
        })
        cls.product_1 = cls.env['product.template'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'taxes_id': [(5, 0, 0)],
            'type': 'consu',
            'list_price': 100.0,
        })
        cls.product_2 = cls.env['product.template'].create({
            'name': 'Product 2',
            'available_in_pos': True,
            'taxes_id': [(5, 0, 0)],
            'type': 'consu',
            'list_price': 200.0,
        })
        cls.attr = cls.env['product.attribute'].create({'name': 'Size'})
        cls.value_small = cls.env['product.attribute.value'].create({'name': 'Small', 'attribute_id': cls.attr.id})
        cls.value_large = cls.env['product.attribute.value'].create({'name': 'Large', 'attribute_id': cls.attr.id})
        cls.product = cls.env['product.template'].create({
            'name': 'Pizza',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': cls.attr.id,
                'value_ids': [(6, 0, [cls.value_small.id, cls.value_large.id])]
            })],
            'urbanpiper_meal_type': '1',
        })
        for ptav in cls.product.attribute_line_ids.product_template_value_ids:
            if ptav.product_attribute_value_id == cls.value_large:
                ptav.price_extra = 2.0
        cls.MockRequest = staticmethod(MockRequest)
        cls.tax_group = cls.env['account.tax.group'].create({
            'name': 'VAT',
        })

        cls.tax_15 = cls.env['account.tax'].create({
            'name': '15% VAT',
            'amount': 15,
            'amount_type': 'percent',
            'tax_group_id': cls.tax_group.id
        })

    def _create_urbanpiper_test_order(self, product, **kwrgs):
        order_identifier = 'keep-it-secret'
        with MockRequest(self.env):
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': product.id,
                'quantity': kwrgs.get('quantity') or 2,
                'delivery_instruction': kwrgs.get('note') or '',
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(order_identifier)
        return self.env['pos.order'].search([('delivery_identifier', '=', order_identifier)], limit=1)


class TestFrontend(TestPosUrbanPiperCommon):

    def test_01_order_flow(self):
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 1,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
            identifier_2 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_2.id,
                'quantity': 1,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_2)
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 1,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(str(uuid.uuid4()))
        self.env['pos.prep.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.urban_piper_config.id)],
        })
        PosOrder = self.env.registry.models['pos.order']

        def mark_urbanpiper_prep_order_as_printed_patch(self):
            # Catch the intentionally raised ValueError from the mathod
            # and return 'False' instead of propagating the exception
            try:
                return super(PosOrder, self).mark_urbanpiper_prep_order_as_printed()
            except ValueError:
                return False
        with patch.object(PosOrder, "mark_urbanpiper_prep_order_as_printed", mark_urbanpiper_prep_order_as_printed_patch):
            self.start_pos_tour('OrderFlowTour', pos_config=self.urban_piper_config, login="pos_admin")
        order_1 = self.env['pos.order'].search([('delivery_identifier', '=', identifier_1)])
        order_2 = self.env['pos.order'].search([('delivery_identifier', '=', identifier_2)])
        self.assertEqual(100.0, order_1.amount_total)
        self.assertEqual(100.0, order_1.amount_paid)
        self.assertEqual(0.0, order_1.amount_difference)
        self.assertEqual(0.0, order_1.amount_tax)
        self.assertEqual(100.0, order_1.payment_ids[0].amount)
        self.assertEqual(200.0, order_2.amount_total)
        self.assertEqual(200.0, order_2.amount_paid)
        self.assertEqual(0.0, order_2.amount_difference)
        self.assertEqual(0.0, order_2.amount_tax)
        self.assertEqual(200.0, order_2.payment_ids[0].amount)
        pdis_order1 = self.env['pos.prep.order'].search([('pos_order_id', '=', order_1.id)], limit=1)
        pdis_order2 = self.env['pos.prep.order'].search([('pos_order_id', '=', order_2.id)], limit=1)
        self.assertEqual(len(pdis_order1.prep_line_ids), 1, "Should have 1 preparation orderlines")
        self.assertEqual(len(pdis_order2.prep_line_ids), 1, "Should have 1 preparation orderlines")

    def test_02_order_with_instruction(self):
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 4,
                'delivery_instruction': 'Make it spicy..',
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
        self.start_pos_tour('OrderWithInstructionTour', pos_config=self.urban_piper_config, login="pos_admin")
        order_1 = self.env['pos.order'].search([('delivery_identifier', '=', identifier_1)])
        self.assertEqual(400.0, order_1.amount_total)
        self.assertEqual(400.0, order_1.amount_paid)
        self.assertEqual(0.0, order_1.amount_tax)
        self.assertEqual(400.0, order_1.payment_ids[0].amount)
        self.assertEqual('Make it spicy..', order_1.general_customer_note)

    def test_03_order_with_charges_and_discount(self):
        self.tax_15.write({
            'fiscal_position_ids': [(4, self.urban_piper_config.urbanpiper_fiscal_position_id.id)],
        })
        self.discount_product = self.env.ref('pos_discount.product_product_consumable', False)
        self.discount_product.taxes_id = [(6, 0, self.tax_15.ids)]
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 5,
                'packaging_charge': 50,
                'delivery_charge': 100,
                'discount_amount': 150,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
        self.start_pos_tour('OrderWithChargesAndDiscountTour', pos_config=self.urban_piper_config, login="pos_admin")
        order_1 = self.env['pos.order'].search([('delivery_identifier', '=', identifier_1)])
        self.assertAlmostEqual(522.51, order_1.amount_total, places=1)
        self.assertAlmostEqual(522.51, order_1.amount_paid, places=1)
        self.assertAlmostEqual(22.51, order_1.amount_tax, places=1)
        self.assertAlmostEqual(522.51, order_1.payment_ids[0].amount, places=1)

    def test_prepare_option_data_returns_valid_options(self):
        """Test that _prepare_option_data returns correctly formatted active options."""
        self.env['res.lang']._activate_lang('fr_FR')
        self.value_small.with_context(lang='fr_FR').name = "Petit"
        self.value_large.with_context(lang='fr_FR').name = "Grand"
        up = UrbanPiperClient(self.urban_piper_config)
        result = up._prepare_option_data(self.product)
        expected = [
            {
                'ref_id': f'{self.product.id}-{self.value_small.id}',
                'title': 'Small',
                'available': True,
                'opt_grp_ref_ids': [f'{self.product.id}-{self.attr.id}'],
                'price': 0.0,
                'food_type': '1',
                'translations': [{'language': 'fr', 'title': 'Petit'}]
            },
            {
                'ref_id': f'{self.product.id}-{self.value_large.id}',
                'title': 'Large',
                'available': True,
                'opt_grp_ref_ids': [f'{self.product.id}-{self.attr.id}'],
                'price': 2.0,
                'food_type': '1',
                'translations': [{'language': 'fr', 'title': 'Grand'}]
            },
        ]
        self.assertEqual(result, expected)

    def test_reject_order(self):
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 5,
                'packaging_charge': 50,
                'delivery_charge': 100,
                'discount_amount': 150,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
        self.start_pos_tour('test_reject_order', pos_config=self.urban_piper_config, login="pos_admin")
        self.assertEqual("cancelled", self.urban_piper_config.current_session_id.order_ids[0].delivery_status)

    def test_order_prep_time(self):
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 5,
                'packaging_charge': 50,
                'delivery_charge': 100,
                'discount_amount': 150,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
        self.start_pos_tour('OrderPrepTime', pos_config=self.urban_piper_config, login="pos_admin")
        order_1 = self.env['pos.order'].search([('delivery_identifier', '=', identifier_1)])
        self.assertEqual(35, order_1.prep_time)

    def test_payment_method_close_session(self):
        def _mock_make_api_request(self, endpoint, method='POST', data=None, timeout=10):
            return []
        self.urban_piper_config.payment_method_ids = self.env['pos.payment.method'].search([]).filtered(lambda pm: pm.type == 'bank')
        with patch.object(UrbanPiperClient, "_make_api_request", _mock_make_api_request):
            self.urban_piper_config.with_user(self.pos_admin).open_ui()
            self.start_pos_tour('test_payment_method_close_session', pos_config=self.urban_piper_config, login="pos_admin")

    def test_multi_branch_tax_setup(self):
        self.parent_company = self.company_data['company']
        self.child_company = self.env['res.company'].create({
            'name': 'Branch Company',
            'parent_id': self.parent_company.id,
            'chart_template': self.env.company.chart_template,
            'country_id': self.env.company.country_id.id,
        })
        bank_payment_method = self.bank_payment_method.copy()
        bank_payment_method.company_id = self.child_company.id
        self.tax_15.write({
            'company_id': self.parent_company.id
        })
        self.tax_group.write({
            'company_id': self.parent_company.id
        })
        self.product_with_tax_15 = self.env['product.template'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'taxes_id': [(4, self.tax_15.id)],
            'type': 'consu',
            'list_price': 100.0,
        })
        self.child_branch_pos_config = self.env['pos.config'].with_company(self.child_company).create({
            'name': 'Branch POS',
            'module_pos_urban_piper': True,
            'urbanpiper_delivery_provider_ids': [Command.set([self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id])],
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_journal_id': self.company_data['default_journal_sale'].id,
            'payment_method_ids': [(4, bank_payment_method.id)],
        })
        self.child_branch_pos_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.child_branch_pos_config.id).create({
                'product_id': self.product_with_tax_15.id,
                'quantity': 5,
                'packaging_charge': 50,
                'delivery_charge': 100,
                'discount_amount': 150,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
        order = self.env['pos.order'].search([('delivery_identifier', '=', identifier_1)])

        def _mock_make_api_request(self, endpoint, method='POST', data=None, timeout=10):
            return []

        with patch.object(UrbanPiperClient, "_make_api_request", _mock_make_api_request):
            self.child_branch_pos_config.order_status_update(order.id, 'Food Ready')
        self.assertEqual(self.tax_15.id, order.lines[0].tax_ids.id)

    def test_to_check_attribute(self):
        self.configurable_chair.active = True
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(
                config_id=self.urban_piper_config.id,
                options_to_add=[
                    {'title': 'Red', 'quantity': '1', 'merchant_id': f'{self.configurable_chair.id}-{self.configurable_chair.attribute_line_ids[0].value_ids[0].id}'},
                    {'title': 'Metal', 'quantity': '1', 'merchant_id': f'{self.configurable_chair.id}-{self.configurable_chair.attribute_line_ids[1].value_ids[0].id}'},
                    {'title': 'Wool', 'quantity': '1', 'merchant_id': f'{self.configurable_chair.id}-{self.chair_fabrics_wool.id}'},
                    {'title': 'Cup Holder', 'quantity': '1', 'merchant_id': f'{self.configurable_chair.id}-{self.chair_addon_cupholder.id}'},
                    {'title': 'Cushion', 'quantity': '1', 'merchant_id': f'{self.configurable_chair.id}-{self.chair_addon_cushion.id}'},
                ],
            ).create({
                'product_id': self.configurable_chair.id,
                'quantity': 2,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
        self.start_pos_tour('test_to_check_attribute', pos_config=self.urban_piper_config, login="pos_admin")

    def test_product_taxes(self):
        self.tax_15.write({
            'fiscal_position_ids': [(4, self.urban_piper_config.urbanpiper_fiscal_position_id.id)],
        })
        self.tax_15.original_tax_ids = [(4, self.tax_15.id)]
        self.product_1.taxes_id = [(4, self.tax_15.id)]
        packaging_product = self.env.ref('pos_urban_piper.product_packaging_charges', False)
        delivery_product = self.env.ref('pos_urban_piper.product_delivery_charges', False)
        packaging_product.taxes_id = [(6, 0, self.tax_15.ids)]
        self.discount_product = self.env.ref('pos_discount.product_product_consumable', False)
        self.discount_product.taxes_id = [(6, 0, self.tax_15.ids)]
        delivery_product.taxes_id = [(5, 0, 0)]
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(
                config_id=self.urban_piper_config.id,
                has_tax=False
            ).create({
                'product_id': self.product_1.id,
                'quantity': 2,
                'delivery_instruction': 'Leave at door',
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
                'packaging_charge': 10.0,
                'delivery_charge': 10.0,
                'discount_amount': 10.0
            }).make_test_order(identifier_1)
        order = self.env['pos.order'].search([('delivery_identifier', '=', identifier_1)])
        self.assertEqual(order.lines[0].tax_ids.id, self.tax_15.id)
        self.assertEqual(order.lines[1].tax_ids.id, self.tax_15.id)
        self.assertEqual(order.lines[2].tax_ids.id, False)
        self.assertEqual(order.lines[3].tax_ids.id, self.tax_15.id)

    def test_inclusive_tax_type_with_normal_order_line(self):
        self.tax_15 = self.env['account.tax'].create({
            'name': '15% VAT Inclusive',
            'amount': 15,
            'amount_type': 'percent',
            'price_include_override': 'tax_included',
        })
        self.product_1.taxes_id = [(6, 0, self.tax_15.ids)]
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 2,
                'delivery_instruction': 'Leave at door',
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id
            }).make_test_order("order_inclusive_tax")
        order = self.env['pos.order'].search([('delivery_identifier', '=', 'order_inclusive_tax')])
        line = order.lines[0]
        self.assertEqual(line.tax_ids.id, self.tax_15.id)
        self.assertAlmostEqual(line.price_unit, 100.0, places=2)
        self.assertAlmostEqual(line.price_subtotal, 173.91, places=2)
        self.assertAlmostEqual(line.price_subtotal_incl, 200.0, places=2)

    def test_charges_sent_to_urbanpiper(self):
        up = UrbanPiperClient(self.urban_piper_config)
        delivery_charge_product = self.env.ref('pos_urban_piper.product_delivery_charges')
        delivery_charge_product.list_price = 10
        charges = up._prepare_charges_data()
        self.assertEqual(
            charges,
            [{'code': 'DC_F', 'title': 'Delivery Charges', 'active': True, 'structure': {'applicable_on': 'order.order_subtotal', 'value': 10.0}, 'item_ref_ids': ['all']}]
        )

    def test_order_with_no_children_taxes(self):
        tax = self.env['account.tax'].create({
            'name': 'Tax without children taxes',
            'amount_type': 'group',
        })
        self.product_1.write({
            'taxes_id': [Command.set([tax.id])],
        })

        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 1,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier)

        order = self.env['pos.order'].search([('delivery_identifier', '=', identifier)])

        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines[0].price_unit, 100.0)
        self.assertEqual(order.lines[0].price_subtotal, 100.0)
        self.assertEqual(order.amount_total, 100.0)
        self.assertEqual(order.amount_tax, 0.0)

    def test_product_level_discount(self):
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            identifier_1 = str(uuid.uuid4())
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id, line_discount=40).create({
                'product_id': self.product_1.id,
                'quantity': 2,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order(identifier_1)
        self.start_pos_tour('test_product_level_discount', pos_config=self.urban_piper_config, login='pos_admin')
        order = self.env['pos.order'].search([('delivery_identifier', '=', identifier_1)])
        self.assertEqual(160.0, order.amount_total)
        self.assertEqual(160.0, order.amount_paid)
        self.assertEqual('paid', order.state)
        self.assertEqual(20, order.lines[0].discount)

    def test_order_cancllaton_status(self):
        self.urban_piper_config.open_ui()
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            self.env['pos.urbanpiper.test.order.wizard'].with_context(config_id=self.urban_piper_config.id).create({
                'product_id': self.product_1.id,
                'quantity': 1,
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id,
            }).make_test_order('order-to-cancel')
        order = self.env['pos.order'].search([('delivery_identifier', '=', 'order-to-cancel')], limit=1)
        self.env['pos.prep.order'].process_order(order.id)
        with MockRequest(self.env):
            UpController = PosUrbanPiperController()
            UpController._order_status_update({
                'order_id': 'order-to-cancel',
                'new_state': 'Cancelled',
                'store_id': self.urban_piper_config.urbanpiper_store_identifier,
            })
        self.assertEqual(order.delivery_status, 'cancelled')
        self.assertEqual(order.state, 'cancel')
        prep_order = self.env['pos.prep.order'].search([('pos_order_id', '=', order.id)])
        prep_line = prep_order.prep_line_ids
        self.assertEqual(len(prep_line), 1)
        self.assertEqual(prep_line.quantity, 1)
        self.assertEqual(prep_line.cancelled, 1)

    def test_category_image_url_payload(self):
        self.urban_piper_config.urbanpiper_webhook_url = 'http://localhost:8069'
        category = self.env['pos.category'].create({'name': 'Test Category', 'sequence': 21})
        up = UrbanPiperClient(self.urban_piper_config)
        category_data = up._prepare_categories_data(category)

        self.assertEqual(len(category_data), 1)
        self.assertEqual(category_data[0]['name'], 'Test Category')
        self.assertEqual(category_data[0]['sort_order'], 21)
        self.assertFalse('img_url' in category_data[0])

        image = """<svg height='180' width='180'>
            <rect width="180" height="180" style="fill: #FF5F1F;" />
            <text fill='#EEE' font-size='96' text-anchor='middle' x='90' y='125'>P</text>
        </svg>"""
        category.image_128 = base64.b64encode(image.encode()).decode()
        category_data = up._prepare_categories_data(category)

        self.assertEqual(len(category_data), 1)
        self.assertEqual(category_data[0]['name'], 'Test Category')
        self.assertTrue('img_url' in category_data[0])
        self.assertIn('http://localhost:8069/web/image/', category_data[0]['img_url'])
