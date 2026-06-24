from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if self.env.company.country_code == 'GT':
            fields += ['country_code', 'commercial_partner_id', 'l10n_latam_identification_type_id']
        return fields
