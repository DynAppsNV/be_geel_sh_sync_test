from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def _dyn_export_fields_to_ignore(self):
        return super()._dyn_export_fields_to_ignore() + [
            # Fields form module account_peppol
            "account_peppol_edi_mode",
        ]
