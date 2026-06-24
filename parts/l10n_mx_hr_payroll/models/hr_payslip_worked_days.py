# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'version_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        mx_worked_days = self.filtered(lambda wd: wd.payslip_id.struct_id.country_id.code == "MX")
        for worked_days in mx_worked_days:
            if worked_days.payslip_id.edited or worked_days.payslip_id.state != 'draft':
                continue
            if not worked_days.version_id or worked_days.code == 'OUT':
                worked_days.amount = 0
                continue
            if not worked_days.payslip_id.date_from or not worked_days.payslip_id.date_to:
                continue

            period_wage = worked_days._get_period_wage()
            amount_rate = worked_days.work_entry_type_id.amount_rate
            worked_days.amount = period_wage * amount_rate
        return super(HrPayslipWorkedDays, self - mx_worked_days)._compute_amount()

    def _get_period_wage(self):
        self.ensure_one()
        if not self.is_paid:
            return 0
        if self.version_id.wage_type == 'hourly':
            return self.version_id.hourly_wage * self.number_of_hours
        else:
            payslip = self.payslip_id
            hourly_wage = payslip.l10n_mx_daily_salary / payslip._get_worked_day_lines_hours_per_day()
            return hourly_wage * self.number_of_hours
