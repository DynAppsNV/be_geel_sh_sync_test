from odoo import models, fields


class PosClockInOut(models.Model):
    _inherit = 'pos.clock.in.out'

    employee_id = fields.Many2one('hr.employee', string='Employee')
