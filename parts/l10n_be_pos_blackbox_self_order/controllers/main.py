from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from odoo import http
from odoo.http import request
from odoo.tools import consteq
from werkzeug.exceptions import Unauthorized


class L10nBePosBlackboxController(PosSelfOrderController):

    def _verify_pos_config_l10n_be(self, access_token, check_active_session=True):
        res = super()._verify_pos_config(access_token, check_active_session=check_active_session)
        if res.l10n_be_blackbox_be_id:
            # For blackbox config, we only allow access to these routes for Kiosk mode
            if res.self_ordering_mode != 'kiosk':
                raise Unauthorized("Invalid access token")
        return res

    @http.route('/l10n_be_pos_blackbox_self_order/clock', auth='public', type='jsonrpc', website=True)
    def l10n_be_pos_blackbox_self_order_clock(self, access_token, config_id, session_id, clock_in=True):
        pos_config = self._verify_pos_config_l10n_be(access_token, check_active_session=False)
        session = request.env['pos.session'].sudo().browse(session_id)
        default_user = pos_config.self_ordering_default_user_id
        if clock_in:
            session.sudo().l10n_be_users_clocked_ids |= default_user
            session.sudo()._create_clock_events(default_user, 'in')
        else:
            session.sudo().l10n_be_users_clocked_ids -= default_user
            session.sudo()._create_clock_events(default_user, 'out')
        return {'success': True}

    @http.route('/l10n_be_pos_blackbox_self_order/handle_blackbox_signature', auth='public', type='jsonrpc', website=True)
    def l10n_be_pos_blackbox_self_order_handle_blackbox_signature(self, access_token, config_id, session_id, payload):
        self._verify_pos_config_l10n_be(access_token, check_active_session=False)
        session = request.env['pos.session'].sudo().browse(session_id)
        session.handle_blackbox_signature(payload)
        return {'success': True}

    @http.route('/l10n_be_pos_blackbox_self_order/get_sale_details', auth='public', type='jsonrpc', website=True)
    def l10n_be_pos_blackbox_self_order_get_sale_details(self, access_token, config_id, session_id):
        self._verify_pos_config_l10n_be(access_token, check_active_session=False)
        sale_details = request.env['report.point_of_sale.report_saledetails'].sudo().get_sale_details(
            False, False, False, [session_id], before_closing=True
        )
        return sale_details

    @http.route('/l10n_be_pos_blackbox_self_order/get_l10n_be_user_report_data', auth='public', type='jsonrpc', website=True)
    def l10n_be_pos_blackbox_self_order_get_l10n_be_user_report_data(self, access_token, config_id, session_id):
        self._verify_pos_config_l10n_be(access_token, check_active_session=False)
        session = request.env['pos.session'].sudo().browse(session_id)
        return session.get_l10n_be_user_report_data(True)

    @http.route('/l10n_be_pos_blackbox_self_order/generate_l10n_z_reports_attachments', auth='public', type='jsonrpc', website=True)
    def l10n_be_pos_blackbox_self_order_generate_l10n_z_reports_attachments(self, access_token, config_id, session_id, sale_details, user_report_data):
        self._verify_pos_config_l10n_be(access_token, check_active_session=False)
        session = request.env['pos.session'].sudo().browse(session_id)
        session.generate_l10n_z_reports_attachments(sale_details, user_report_data)
        return {'success': True}

    @http.route('/l10n_be_pos_blackbox_self_order/save_order_signature', auth='public', type='jsonrpc', website=True)
    def l10n_be_pos_blackbox_self_order_save_order_signature(self, access_token, order_id, order_access_token, signature_data):
        self._verify_pos_config_l10n_be(access_token, check_active_session=False)
        allowed_fields = {
            'l10n_be_short_signature', 'l10n_be_event_label', 'l10n_be_event_counter',
            'l10n_be_total_counter', 'l10n_be_fdm_id', 'l10n_be_fdm_date_time',
            'l10n_be_pos_id', 'l10n_be_terminal_id', 'l10n_be_device_id',
            'l10n_be_verification_url', 'l10n_be_pos_date_time', 'l10n_be_vat_calc',
        }
        safe_data = {k: v for k, v in signature_data.items() if k in allowed_fields}
        order = request.env['pos.order'].sudo().browse(order_id)
        if order.exists() and consteq(order.access_token, order_access_token) and safe_data:
            order.write(safe_data)
        return {'success': True}
