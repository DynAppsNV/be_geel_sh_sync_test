from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    l10n_be_vats = fields.Json(string="l10n_be VATs JSON")

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['l10n_be_vats']
        return params
