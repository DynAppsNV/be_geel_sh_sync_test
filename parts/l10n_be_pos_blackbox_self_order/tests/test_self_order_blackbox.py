import odoo.tests
from odoo import Command
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@odoo.tests.tagged("post_install_l10n", "post_install", "-at_install")
class TestSelfOrderBlackbox(TestFrontendCommon):

    @classmethod
    @TestFrontendCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()
        blackbox_be = cls.env['pos.blackbox.be'].sudo().create({
            'fdm_id': 'VCB01002601',
            'display_name': "Blackbox - 123456789",
            'name': "Blackbox - 123456789",
            'local_ip': "0.0.0.0",
        })
        cls.pos_categ_blackbox = cls.env['pos.category'].create({
            'name': 'Blackbox products',
        })

        # Create a product with a price 0, so we can have a tour that go to the confirmation page (no payment needed since price is 0) and sign the order with the blackbox
        cls.product = cls.env['product.product'].create({
            'name': 'Test product',
            'is_storable': True,
            'list_price': 0,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, cls.pos_categ_blackbox.id)],
            'default_code': '12345',
        })
        cls.pos_config.write({
            'payment_method_ids': [Command.set([cls.bank_payment_method.id])],
            'l10n_be_blackbox_be_id': blackbox_be.id,
            'l10n_be_pos_id': 'CPOS0031234567',
            'establishment_number': '8789456149',
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'iface_available_categ_ids': [Command.set([cls.pos_categ_blackbox.id])],
            'epson_printer_ip': '127.0.0.1:8069/receipt_receiver',
        })
        cls.env.user.l10n_be_insz_or_bis_number = '00000000097'
        cls.pos_user.l10n_be_insz_or_bis_number = '00000000097'
        cls.pos_admin.sudo().l10n_be_insz_or_bis_number = '00000000097'
        cls.env.company.write({
            'street': 'Rue de Ramilles 1',
            'vat': 'BE0477472701',
        })

    def test_l10n_be_pos_blackbox_kiosk_tour(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        current_session = self.pos_config.current_session_id
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_l10n_be_pos_blackbox_kiosk_tour")
        pdf_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'pos.session'),
            ('res_id', '=', current_session.id),
            ('mimetype', '=', 'application/pdf')
        ])
        self.assertEqual(len(pdf_attachments), 2, "There should be 2 PDF attachments (Sale Details and User Report).")
        # Two clock events (one in, one out)
        self.assertEqual(len(current_session.pos_clock_in_out_ids), 2)
