# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_line_data_for_external_taxes(self):
        """ Override to set the operation_type per line. """
        res = super()._get_line_data_for_external_taxes()
        if not self.company_id.l10n_br_is_icbs:
            return res

        for line in res:
            line['cbs_ibs_deduction'] = line['base_line']['record'].l10n_br_cbs_ibs_deduction

        return res

    def _l10n_br_remove_informative_taxes(self, payload):
        """ Override to keep the new fiscal reform taxes. """
        if not self.company_id.l10n_br_is_icbs:
            return super()._l10n_br_remove_informative_taxes(payload)

        def is_fiscal_reform_tax(code):
            return any(code.startswith(prefix) for prefix in ("is", "ibs", "cbs"))

        for line in payload.get("lines", []):
            line["taxDetails"] = [
                detail for detail in line["taxDetails"]
                if is_fiscal_reform_tax(detail["taxType"]) or detail["taxImpact"]["impactOnFinalPrice"] != "Informative"
            ]

        tax_highlights = payload.get("summary", {}).get("taxImpactHighlights", {})
        if "informative" in tax_highlights:
            for informative_tax in tax_highlights.get("informative", []):
                tax_code = informative_tax["taxType"]
                if not is_fiscal_reform_tax(tax_code):
                    del payload["summary"]["taxByType"][tax_code]

            tax_highlights["informative"] = [highlight for highlight in tax_highlights["informative"] if is_fiscal_reform_tax(highlight["taxType"])]
