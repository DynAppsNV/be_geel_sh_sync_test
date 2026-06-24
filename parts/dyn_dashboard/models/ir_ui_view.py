from odoo import fields, models


class View(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(
        selection_add=[("dyn_dashboard", "DynApps Dashboard")],
        ondelete={"dyn_dashboard": "cascade"},
    )

    def _get_view_info(self):
        res = super()._get_view_info()
        res["dyn_dashboard"] = {"icon": "oi oi-search", "multi_record": False}
        return res
