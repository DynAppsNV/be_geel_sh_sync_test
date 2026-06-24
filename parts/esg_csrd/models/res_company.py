from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @property
    def ESG_REPORT_DEFAULT_COMPANY(self):
        esg_company_id = False
        try:
            esg_company_id = int(self.env['ir.config_parameter'].sudo().get_param('esg_csrd.esg_main_company'))
        except ValueError:
            return self.browse()
        return self.browse(esg_company_id) or self.env.company
