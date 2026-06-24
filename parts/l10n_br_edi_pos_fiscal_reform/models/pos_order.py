# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_line_data_for_external_taxes(self):
        """ Override. """
        res = super()._get_line_data_for_external_taxes()

        for line in res:
            base_line = line['base_line']
            if base_line['record'].company_id.l10n_br_is_icbs:
                line['operation_type'] = base_line['product_id'].l10n_br_operation_type_pos_id or line['operation_type']

        return res
