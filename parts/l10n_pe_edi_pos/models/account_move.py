# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        self.filtered(lambda am: am.sudo().pos_order_ids and am.company_id.country_code == 'PE').edi_document_ids.filtered(
                lambda d: d.state == 'to_send')._process_documents_web_services(job_count=1)
        return posted

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        if self.env.company.country_code == 'PE':
            result += ['l10n_latam_document_type_id']
        return result
