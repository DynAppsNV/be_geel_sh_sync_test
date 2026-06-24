from odoo import api, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        models = super()._load_pos_data_models(config)
        if config.is_guatemalan_company:
            models.append('l10n_latam.identification.type')
        return models
