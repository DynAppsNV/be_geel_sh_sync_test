from odoo import fields, models


class DynDashboardTile(models.Model):
    _inherit = "xx.dashboard.tile"

    odoo_record_wildcard = fields.Char(
        default="rec.id = %RECORDID",
        help="Wildcard replace for record id where clause when navigating from smartbutton",
    )
    dashboard_model_ids = fields.Many2many(related="dashboard_id.model_ids")

    def query_wildcard_replace(self, query):
        query = super().query_wildcard_replace(query)
        query = self.replace_record_id(query)
        return query

    def replace_record_id(self, query):
        if self.env.context.get("odoo_record_id"):
            res = query.replace("%RECORDID", str(self.env.context.get("odoo_record_id")))
        else:
            res = query.replace(self.odoo_record_wildcard, "1=1")
        return res
