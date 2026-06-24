from odoo import models


class Partner(models.Model):
    _inherit = "res.partner"

    def _dyn_export_fields_to_ignore(self):
        return super()._dyn_export_fields_to_ignore() + [
            "customer_rank",
            "supplier_rank",
            # Fields from module account_followup
            "followup_next_action_date",
            # Fields from module account_peppol
            "peppol_verification_state",
        ]
