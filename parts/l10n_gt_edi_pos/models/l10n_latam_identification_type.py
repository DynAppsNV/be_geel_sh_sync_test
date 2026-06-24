from odoo import api, models


class L10n_LatamIdentificationType(models.Model):
    _name = 'l10n_latam.identification.type'
    _inherit = ['l10n_latam.identification.type', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if config.is_guatemalan_company:
            fields.append('country_id')
        return fields
