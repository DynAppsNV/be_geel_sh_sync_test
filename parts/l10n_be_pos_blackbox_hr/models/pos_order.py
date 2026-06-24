from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_cashier(self):
        self.ensure_one()
        return self.employee_id or super()._get_cashier()
