from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _get_chart_template_data(self, chart_template):
        data = super()._get_chart_template_data(chart_template)
        if self.env.context.get("dyn_export_load_chart_template", False):
            for _company_id, company_data in data["res.company"].items():
                company_data.pop("anglo_saxon_accounting", None)
        return data
