from odoo import models, api


class UserReport(models.AbstractModel):
    _name = "report.l10n_be_pos_blackbox.user_report_template"
    _description = 'POS Session user report'

    @api.model
    def _get_report_values(self, docids, data=None):
        session = self.env['pos.session'].browse(docids).ensure_one()
        values = data if data and self.env.context.get('skip_sale_details_compute') else session.get_l10n_be_user_report_data()
        return {"data": values, "docs": session}
