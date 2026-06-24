# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from datetime import date
import calendar

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_mx_daily_salary = fields.Float('MX: Daily Salary', compute='_compute_daily_salary')
    l10n_mx_years_worked = fields.Integer('MX: Years Worked', compute='_compute_integration_factor')
    l10n_mx_days_of_year = fields.Integer('MX: Days of the Year', compute='_compute_days_of_year')
    l10n_mx_integration_factor = fields.Float('MX: Integration Factor', compute='_compute_integration_factor')

    @api.depends('version_id.wage', 'version_id.schedule_pay')
    def _compute_daily_salary(self):
        for payslip in self:
            payslip.l10n_mx_daily_salary = payslip.version_id.wage / payslip._rule_parameter('l10n_mx_schedule_table')[payslip.version_id.schedule_pay]

    @api.depends('date_to')
    def _compute_days_of_year(self):
        for payslip in self:
            year = payslip.date_to.year
            payslip.l10n_mx_days_of_year = (date(year, 12, 31) - date(year, 1, 1)).days + 1

    @api.depends('l10n_mx_days_of_year', 'date_from', 'date_to', 'version_id')
    def _compute_integration_factor(self):
        for payslip in self:
            start_date = (
                payslip.employee_id.with_context(before_date=payslip.date_from)._get_first_contract_date()
                or payslip.employee_id._get_first_contract_date()
            )
            payslip.l10n_mx_years_worked = payslip.date_to.year - start_date.year
            if start_date <= payslip.date_to + relativedelta(year=start_date.year):
                payslip.l10n_mx_years_worked += 1
            holidays_count = payslip._rule_parameter('l10n_mx_holiday_tables')[payslip.l10n_mx_years_worked]
            holiday_bonus_factor = holidays_count * payslip.version_id.l10n_mx_holiday_bonus_rate / 100

            number_of_days_year = payslip.l10n_mx_days_of_year
            payslip.l10n_mx_integration_factor = (holiday_bonus_factor + payslip._rule_parameter('l10n_mx_christmas_bonus') + number_of_days_year) / number_of_days_year

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_mx_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/salary_rules/hr_salary_rule_christmas_bonus_data.xml',
                'data/salary_rules/hr_salary_rule_regular_pay_data.xml',
            ])]

    def _get_payslips_in_month(self):
        self.ensure_one()
        first_day_of_month = self.date_from.replace(day=1)
        return self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('structure_code', '=', 'MX_REGULAR'),
            ('state', 'in', ['paid', 'validated']),
            ('date_to', '>=', first_day_of_month),
            ('date_from', '<', first_day_of_month + relativedelta(months=1))
        ])

    def _get_accumulated_monthly_subsidy(self):
        payslips_in_month = self._get_payslips_in_month()
        line_values = payslips_in_month._get_line_values(['SUBSIDY_CURRENT_MONTH', 'SUBSIDY_NEXT_MONTH'])

        accumulated_subsidy = 0.0
        for slip in payslips_in_month:
            subsidy_code = (
                'SUBSIDY_CURRENT_MONTH'
                if slip.date_from.month == self.date_from.month
                else 'SUBSIDY_NEXT_MONTH'
            )
            accumulated_subsidy += line_values[subsidy_code][slip.id]['total']

        return accumulated_subsidy

    @api.model
    def _schedule_timedelta(self, schedule, date_from, country_code=False):
        if country_code == 'MX':
            if schedule == '10_days':
                return relativedelta(days=9)
            elif schedule == '14_days':
                return relativedelta(days=13)
            elif schedule == 'bi-weekly':
                days_in_month = calendar.monthrange(date_from.year, date_from.month)[1]
                return relativedelta(day=15 if date_from.day <= 15 else days_in_month)
            elif schedule == 'bi-monthly':
                return relativedelta(months=2, days=-1)

        return super()._schedule_timedelta(schedule, date_from, country_code)

    def _get_schedule_days(self):
        self.ensure_one()
        if self.is_wrong_duration:
            return (self.date_to - self.date_from).days + 1
        return self._rule_parameter('l10n_mx_schedule_table')[self.version_id.schedule_pay]

    def _get_worked_day_lines(self, domain=None, check_out_of_version=True):
        self.ensure_one()
        version = self.version_id
        if (
            self.struct_id.country_id.code != 'MX'
            or not check_out_of_version
            or version.work_entry_source != 'calendar'
        ):
            return super()._get_worked_day_lines(domain, check_out_of_version)

        worked_days_vals_list = self._get_worked_day_lines_values(domain=domain)

        attendance_entry_type = self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)
        out_of_contract_entry_type = self.env.ref('hr_work_entry.hr_work_entry_type_out_of_contract', raise_if_not_found=False)
        attendance_vals = next((wd for wd in worked_days_vals_list if wd['work_entry_type_id'] == attendance_entry_type.id), None)

        hours_per_day = self._get_worked_day_lines_hours_per_day() or 8.0
        schedule_days = self._get_schedule_days()

        if (
            out_of_contract_entry_type
            and (
                version.contract_date_start > self.date_from
                or (version.contract_date_end and version.contract_date_end < self.date_to)
            )
        ):
            date_from = max(version.contract_date_start, self.date_from)
            date_to = min(version.contract_date_end or self.date_to, self.date_to)
            period_days = (date_to - date_from).days + 1
            out_of_contract_days = schedule_days - period_days
            worked_days_vals_list.append({
                'sequence': out_of_contract_entry_type.sequence,
                'work_entry_type_id': out_of_contract_entry_type.id,
                'number_of_days': out_of_contract_days,
                'number_of_hours': out_of_contract_days * hours_per_day,
            })

        if attendance_vals:
            entry_type_ids = [wd['work_entry_type_id'] for wd in worked_days_vals_list]
            extra_hours_entry_types = self.env['hr.work.entry.type'].browse(entry_type_ids).filtered(lambda et: et.is_extra_hours)
            recorded_hours = sum(
                wd['number_of_hours']
                for wd in worked_days_vals_list
                if wd['work_entry_type_id'] not in extra_hours_entry_types.ids
            )

            hours_to_adjust = schedule_days * hours_per_day - recorded_hours
            days_to_adjust = round(hours_to_adjust / hours_per_day, 5) if hours_per_day else 0.0

            attendance_vals['number_of_hours'] += hours_to_adjust
            attendance_vals['number_of_days'] += self._round_days(attendance_entry_type, days_to_adjust)

        return worked_days_vals_list
