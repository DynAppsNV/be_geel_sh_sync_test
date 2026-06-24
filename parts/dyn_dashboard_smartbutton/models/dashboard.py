from odoo import api, fields, models


class DynDashboard(models.Model):
    _inherit = "xx.dashboard"
    _description = "DynApps Dashboard"

    model_ids = fields.Many2many("ir.model")
    icon = fields.Char(help="Use the font awesome class name. E.g. 'fa-thermometer-full'")

    @api.model
    def fetch_dashboard_data(self, dashboard_id):
        dashboard_data = super().fetch_dashboard_data(dashboard_id)
        dashboard_data["odoo_record_id"] = self.env.context.get("odoo_record_id")
        return dashboard_data
