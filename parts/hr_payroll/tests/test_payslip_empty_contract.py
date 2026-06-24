# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.fields import Date, Datetime
from odoo.tests import tagged, freeze_time
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase


@tagged('post_install', '-at_install')
class TestPayslipNewEmployeeToday(TestPayslipContractBase):

    def _month_bounds(self, base_date):
        date_from = base_date.replace(day=1)
        date_to = date_from + relativedelta(months=1, days=-1)
        return date_from, date_to

    def _assert_full_out_of_contract(self, slip, date_from, date_to, lines, expected_duration):
        out_type = self.env.ref('hr_work_entry.hr_work_entry_type_out_of_contract', raise_if_not_found=False)
        self.assertTrue(out_type, "Missing 'Out of Contract' type")

        out_lines = [l for l in lines if l.get('work_entry_type_id') == out_type.id]
        self.assertTrue(out_lines, "Missing 'Out of Contract' line in payslip")
        self.assertEqual(len(out_lines), 1, f"Expected exactly one 'Out of Contract' line, got {len(out_lines)}")
        out_line = out_lines[0]

        self.assertAlmostEqual(out_line['number_of_days'], expected_duration['days'], places=2)
        self.assertAlmostEqual(out_line['number_of_hours'], expected_duration['hours'], places=2)

        other_lines = [l for l in lines if l is not out_line]
        self.assertFalse(other_lines, "Expected only 'Out of Contract' line")

    def _make_new_employee_no_contract(self):
        emp = self.env['hr.employee'].create({
            'name': 'Employee Without Contract',
            'company_id': self.company_us.id,
            'resource_calendar_id': self.calendar_richard.id,
        })
        version = emp.version_id
        self.assertEqual(version.date_version, Date.today())
        self.assertFalse(version.contract_date_start)
        return emp, version

    def _make_draft_payslip(self, emp, version, date_from, date_to):
        return self.env['hr.payslip'].new({
            'name': 'Draft',
            'employee_id': emp.id,
            'version_id': version.id,
            'company_id': emp.company_id.id,
            'date_from': date_from,
            'date_to': date_to,
        })

    def _assert_no_work_entries(self, emp, date_from, date_to):
        emp.version_id.generate_work_entries(date_from, date_to)

        dt_from = Datetime.to_datetime(date_from)
        dt_to = Datetime.to_datetime(date_to) + relativedelta(hour=23, minute=59, second=59)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', emp.id),
            ('date', '>=', dt_from),
            ('date', '<=', dt_to),
        ], limit=1)

        self.assertFalse(
            work_entries,
            f"Expected no work entries for {emp.name} between {date_from} and {date_to}, "
            f"but found at least one."
        )

    def test_employee_without_contract_payslip_current_month(self):
        with freeze_time(date(2025, 12, 20)):
            emp, version = self._make_new_employee_no_contract()

            date_from, date_to = self._month_bounds(Date.today())

            slip = self._make_draft_payslip(emp, version, date_from, date_to)
            lines = slip._get_worked_day_lines(domain=None, check_out_of_version=True)

            expected_duration = {'days': 23.0, 'hours': 184.0}
            self._assert_full_out_of_contract(slip, date_from, date_to, lines, expected_duration)
            self._assert_no_work_entries(emp, date_from, date_to)

    def test_employee_without_contract_payslip_previous_month(self):
        with freeze_time(date(2025, 12, 20)):
            emp, version = self._make_new_employee_no_contract()

            prev_month_date = Date.today() + relativedelta(months=-1)
            date_from, date_to = self._month_bounds(prev_month_date)

            slip = self._make_draft_payslip(emp, version, date_from, date_to)
            lines = slip._get_worked_day_lines(domain=None, check_out_of_version=True)

            expected_duration = {'days': 20.0, 'hours': 160.0}
            self._assert_full_out_of_contract(slip, date_from, date_to, lines, expected_duration)
            self._assert_no_work_entries(emp, date_from, date_to)

    def test_employee_without_contract_payslip_next_month(self):
        with freeze_time(date(2025, 12, 20)):
            emp, version = self._make_new_employee_no_contract()

            next_month_date = Date.today() + relativedelta(months=1)
            date_from, date_to = self._month_bounds(next_month_date)

            slip = self._make_draft_payslip(emp, version, date_from, date_to)
            lines = slip._get_worked_day_lines(domain=None, check_out_of_version=True)

            expected_duration = {'days': 22.0, 'hours': 176.0}
            self._assert_full_out_of_contract(slip, date_from, date_to, lines, expected_duration)
            self._assert_no_work_entries(emp, date_from, date_to)
