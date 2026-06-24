from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def write(self, vals):
        if not vals.get("active", True):
            self._unlink_except_contains_journal_items()
            self._unlink_except_linked_to_fiscal_position()
            self._unlink_except_linked_to_tax_repartition_line()
        return super().write(vals)
