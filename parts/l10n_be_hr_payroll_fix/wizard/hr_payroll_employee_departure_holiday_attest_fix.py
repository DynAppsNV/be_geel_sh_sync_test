from odoo import fields, models


class HrPayslipEmployeeDepatureHolidayAttestsTimeOffLine(models.TransientModel):
    _inherit = 'hr.payslip.employee.depature.holiday.attests.time.off.line'

    leave_allocation_count = fields.Float(string='Allocations', digits='Leave Units')
    leave_count = fields.Float(string="Leaves", digits='Leave Units')
