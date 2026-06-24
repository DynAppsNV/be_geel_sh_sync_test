from odoo import api, models


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_self_data_fields(self, pos_config_id):
        fields = super()._load_pos_self_data_fields(pos_config_id)
        if pos_config_id.l10n_be_blackbox_be_id:
            fields += ['l10n_be_users_clocked_ids', 'booking_period_id']
        return fields

    # TODO-manv: FW- 19.1: directly contact OBOX via backend to sign mobile orders
    def get_unsigned_mobile_orders(self):
        self.ensure_one()
        orders = self.env['pos.order'].search([
            ('session_id', '=', self.id),
            ('source', '=', 'mobile'),
            ('state', '=', 'paid'),
            ('l10n_be_short_signature', '=', False),
        ])
        return orders.ids
