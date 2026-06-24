from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def write(self, vals):
        res = super().write(vals)
        if 'l10n_be_insz_or_bis_number' in vals:
            if self.employee_id:
                self.employee_id.write({'l10n_be_insz_or_bis_number': self.l10n_be_insz_or_bis_number})
        return res
