from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    l10n_be_insz_or_bis_number = fields.Char(related='employee_id.l10n_be_insz_or_bis_number')
