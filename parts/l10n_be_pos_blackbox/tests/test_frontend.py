import odoo
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nBePosBlackbox(TestFrontendCommon):

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

        cls.main_pos_config.write({
            'l10n_be_blackbox_be_id': blackbox_be.id,
            'l10n_be_pos_id': 'CPOS0031234567',
            'epson_printer_ip': '127.0.0.1:8069/receipt_receiver',
            'other_devices': True,
            'establishment_number': '8789456149'
        })
        cls.env.user.l10n_be_insz_or_bis_number = '00000000097'
        cls.pos_user.l10n_be_insz_or_bis_number = '00000000097'
        cls.pos_admin.sudo().l10n_be_insz_or_bis_number = '00000000097'
        cls.env.company.write({
            'street': 'Rue de Ramilles 1',
            'vat': 'BE0477472701',
        })

    def _assert_session_event_counters(self, session, expected):
        self.assertEqual(session.l10n_be_N_event_counter, expected.get("N_event_counter", 0))
        self.assertEqual(session.l10n_be_N_event_amount, expected.get("N_event_amount", 0))
        self.assertEqual(session.l10n_be_P_event_counter, expected.get("P_event_counter", 0))
        self.assertEqual(session.l10n_be_P_event_amount, expected.get("P_event_amount", 0))
        self.assertEqual(session.l10n_be_I_event_counter, expected.get("I_event_counter", 0))
        self.assertEqual(session.l10n_be_I_event_amount, expected.get("I_event_amount", 0))
        self.assertEqual(session.l10n_be_T_event_counter, expected.get("T_event_counter", 0))
        self.assertEqual(session.l10n_be_T_event_amount, expected.get("T_event_amount", 0))

    def test_l10n_be_pos_blackbox_sign_sale_refund_tour(self):
        """ Test signing a sale and a refund """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'l10n_be_pos_blackbox_sign_sale_refund_tour', login="pos_admin")
        self._assert_session_event_counters(session, {
            "N_event_counter": 4,
            "N_event_amount": 2.2,
            "P_event_counter": 1,
            "P_event_amount": 4.4,
        })
        self.assertEqual(len(session.pos_clock_in_out_ids), 1)

    def test_l10n_be_pos_blackbox_sign_sale_invoice_tour(self):
        """ Test signing a sale with an invoice """
        self.partner_bbox = self.env["res.partner"].create({"name": "A blackbox partner"})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'l10n_be_pos_blackbox_sign_sale_invoice_tour', login="pos_admin")
        self._assert_session_event_counters(session, {
            "N_event_counter": 1,
            "N_event_amount": 2.2,
            "P_event_counter": 2,
            "P_event_amount": 2.2,
            "I_event_counter": 1,
            "I_event_amount": 2.2,
        })
        self.assertEqual(len(session.pos_clock_in_out_ids), 1)

    def test_l10n_be_pos_blackbox_merge_transfer_tour(self):
        """ Test to merge/transfer orders between tables """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'l10n_be_pos_blackbox_transfer_tour', login="pos_admin")
        self._assert_session_event_counters(session, {
            "N_event_counter": 1,
            "N_event_amount": 6.6,
            "P_event_counter": 6,
            "P_event_amount": 6.6,
        })
        self.assertEqual(len(session.pos_clock_in_out_ids), 1)

    def test_l10n_be_pos_blackbox_split_table_tour(self):
        """ Test to split/transfer orders between tables """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'l10n_be_pos_blackbox_split_table_tour', login="pos_admin")
        self._assert_session_event_counters(session, {
            "N_event_counter": 2,
            "N_event_amount": 6.6,
            "P_event_counter": 6,
            "P_event_amount": 11,
        })

    def test_l10n_be_pos_blackbox_cash_move_cancel_order_tour(self):
        """ Test that cancel an order then make a cash move """
        self.pos_admin.write({
            'group_ids': [
                (4, self.env.ref('account.group_account_basic').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'l10n_be_pos_blackbox_cash_move_cancel_order_tour', login="pos_admin")
        self._assert_session_event_counters(session, {
            "N_event_counter": 1,
            "P_event_counter": 2,
            "P_event_amount": 0,
        })
        self.assertEqual(len(session.pos_clock_in_out_ids), 1)

    def test_l10n_be_pos_blackbox_sign_sale_backend_offline(self):
        """ Test signing a sale when the backend is unreachable """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'test_l10n_be_pos_blackbox_sign_sale_backend_offline', login="pos_admin")
        # Check that the order that was signed offline, is now synced with its blackbox signature
        signed_order = self.env["pos.order"].search([('session_id', '=', session.id)])
        self.assertEqual(len(signed_order), 1, "There should be one signed order.")
        self.assertEqual(signed_order.l10n_be_short_signature, "ca39a3ee5e6b4b0d3255bfef95601890afd80709")
        self.assertEqual(signed_order.state, "paid")
        self._assert_session_event_counters(session, {
            "N_event_counter": 1,
            "N_event_amount": 2.2,
        })
        self.assertEqual(len(session.pos_clock_in_out_ids), 1)

    def test_l10n_be_pos_blackbox_sign_sale_blackbox_offline(self):
        """ Test that we should not be able to confirm a sale when the blackbox is unreachable """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'test_l10n_be_pos_blackbox_sign_sale_blackbox_offline', login="pos_admin")
        # Check that the order that was attempted to be signed offline, is still in draft and has no blackbox signature
        order = self.env["pos.order"].search([('session_id', '=', session.id)])
        self.assertEqual(len(order), 1, "There should be one order.")
        self.assertFalse(order.l10n_be_short_signature)
        self.assertEqual(order.state, "draft")
        # Here the 'order' P event is not counted despite the order is synced, because P events are not awaited, and the tour finish before the P event is processed
        self._assert_session_event_counters(session, {})
        self.assertEqual(len(session.pos_clock_in_out_ids), 1)

    def test_l10n_be_pos_blackbox_sign_sale_backend_offline_blackbox_offline(self):
        """ Test that we should not be able to confirm a sale when the blackbox and the backend are unreachable """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'test_l10n_be_pos_blackbox_sign_sale_backend_offline_blackbox_offline', login="pos_admin")
        # Check that the order that was attempted to be signed offline, is still in draft and has no blackbox signature
        order = self.env["pos.order"].search([('session_id', '=', session.id)])
        self.assertEqual(len(order), 1, "There should be one order.")
        self.assertFalse(order.l10n_be_short_signature)
        self.assertEqual(order.state, "draft")
        # Here the 'order' P event is not counted despite the order is synced, because P events are not awaited, and the tour finish before the P event is processed
        self._assert_session_event_counters(session, {})
        self.assertEqual(len(session.pos_clock_in_out_ids), 1)

    def test_l10n_be_pos_blackbox_be_close_session_z_reports(self):
        """ Test that closing a session generates the Z reports as PDF attachments """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        current_session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'l10n_be_pos_blackbox_be_close_session_z_reports', login="accountman")
        pdf_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'pos.session'),
            ('res_id', '=', current_session.id),
            ('mimetype', '=', 'application/pdf')
        ])
        self.assertEqual(len(pdf_attachments), 2, "There should be 2 PDF attachments (Sale Details and User Report).")
        self._assert_session_event_counters(current_session, {
            "N_event_counter": 1,
            "N_event_amount": 2.2,
        })
        # Two clock events (one in, one out)
        self.assertEqual(len(current_session.pos_clock_in_out_ids), 2)
