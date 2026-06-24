from odoo import models, api


class IrUiView(models.Model):
    _name = 'ir.ui.view'
    _inherit = ['pos.load.mixin', 'ir.ui.view']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name']

    @api.model
    def _load_pos_data_search_read(self, data, config):
        res = super()._load_pos_data_search_read(data, config)
        # Loading views ID here instead of '_load_pos_data_domain' to avoid Access Error on 'ir.ui.view'
        res.append({
            "id": self.env.ref('l10n_be_pos_blackbox.pos_session_reports_list_view').id,
            "name": "pos_session_reports_list_view",
        })
        return res

    @api.model
    def _load_pos_data_domain(self, data, config):
        return False
