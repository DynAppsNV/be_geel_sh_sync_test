# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.fields import Date, Datetime
from odoo.tests.common import tagged, freeze_time
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


@tagged('work_entry')
class TestWorkEntry(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})

    def _month_bounds(self, base_date):
        date_from = base_date.replace(day=1)
        date_to = date_from + relativedelta(months=1, days=-1)
        return date_from, date_to

    def _get_work_entry_types(self):
        out_type = self.env.ref('hr_work_entry.hr_work_entry_type_out_of_contract', raise_if_not_found=False)
        self.assertTrue(out_type, "Missing 'Out of Contract' type")
        att_type = self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)
        self.assertTrue(att_type, "Missing 'Attendance' type")
        return out_type, att_type

    def _get_entries_by_type(self, employee, date_from, date_to):
        out_type, att_type = self._get_work_entry_types()
        start_dt = Datetime.to_datetime(date_from)
        stop_dt = Datetime.to_datetime(date_to) + relativedelta(hour=23, minute=59, second=59)

        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', employee.id),
            ('date', '<=', stop_dt),
            ('date', '>=', start_dt),
        ])
        by_type = {
            'attendance': work_entries.filtered(lambda w: w.work_entry_type_id.id == att_type.id),
            'out': work_entries.filtered(lambda w: w.work_entry_type_id.id == out_type.id),
        }
        return by_type

    def _assert_attendance_in_range(self, employee, date_from, date_to, expected_we_number):
        if date_from <= date_to:
            by_type = self._get_entries_by_type(employee, date_from, date_to)
            att = by_type['attendance']
            self.assertTrue(att, "Expected Attendance work entries, got none.")
            earliest, latest = min(att.mapped('date')), max(att.mapped('date'))
            self.assertEqual(
                earliest, date_from,
                f"Attendance work entries start on {earliest}, expected {date_from}."
            )
            self.assertEqual(
                latest, date_to,
                f"Attendance work entries end on {earliest}, expected {date_to}."
            )
            self.assertEqual(
                len(att), expected_we_number,
                f"Got {len(att)} attendance work entries, expected {expected_we_number}."
            )

    def _assert_no_attendance_in_range(self, employee, date_from, date_to):
        by_type = self._get_entries_by_type(employee, date_from, date_to)
        self.assertFalse(by_type['attendance'],
                         f"Expected no Attendance work entries, got {len(by_type['attendance'])}.")

    def _assert_worked_days_lines(self, slip, expected_out, expected_att):
        lines = slip._get_worked_day_lines(domain=None, check_out_of_version=True)
        out_type, att_type = self._get_work_entry_types()

        out_lines = [l for l in lines if l.get('work_entry_type_id') == out_type.id]
        att_lines = [l for l in lines if l.get('work_entry_type_id') == att_type.id]

        self.assertEqual(len(out_lines), 1, f"Expected exactly one 'Out of Contract' line, got {len(out_lines)}")
        out_line = out_lines[0]
        self.assertAlmostEqual(out_line['number_of_days'], expected_out['days'], places=2)
        self.assertAlmostEqual(out_line['number_of_hours'], expected_out['hours'], places=2)

        if abs(expected_att['days']) < 1e-12 and abs(expected_att['hours']) < 1e-12:
            if att_lines:
                self.assertEqual(len(att_lines), 1, f"Expected at most one 'Attendance' line, got {len(att_lines)}")
                att_line = att_lines[0]
                self.assertAlmostEqual(att_line['number_of_days'], 0.0, places=2)
                self.assertAlmostEqual(att_line['number_of_hours'], 0.0, places=2)
        else:
            self.assertEqual(len(att_lines), 1, f"Expected exactly one 'Attendance' line, got {len(att_lines)}")
            att_line = att_lines[0]
            self.assertAlmostEqual(att_line['number_of_days'], expected_att['days'], places=2)
            self.assertAlmostEqual(att_line['number_of_hours'], expected_att['hours'], places=2)

    def test_work_entries_contract_starts_this_month(self):
        """
        Contract starts during current month.
        Checks:
          - current month: Out-of-contract before start, Attendance after start, work entries only for attendance days
          - previous month: full Out-of-contract, no work entries
        """
        with freeze_time(date(2025, 12, 20)):
            cal = self.calendar_40h

            month_start, month_end = self._month_bounds(Date.today())
            prev_start, prev_end = self._month_bounds(Date.today() + relativedelta(months=-1))

            contract_start = date(2025, 12, 10)

            emp = self.env['hr.employee'].create({
                'name': 'John Doe',
                'company_id': self.company_us.id,
                'resource_calendar_id': cal.id,
                'contract_date_start': contract_start,
            })
            version = emp.version_id

            #  Current month
            work_entries = version.generate_work_entries(month_start, month_end)
            work_entries.action_validate()
            self._assert_attendance_in_range(emp, contract_start, month_end, expected_we_number=16.0)
            self._assert_no_attendance_in_range(emp, month_start, contract_start + relativedelta(days=-1))

            slip = self.env['hr.payslip'].new({
                'name': 'Payslip Dec 2025',
                'employee_id': emp.id,
                'version_id': version.id,
                'company_id': emp.company_id.id,
                'date_from': month_start,
                'date_to': month_end,
            })
            expected_out = {'days': 7.0, 'hours': 56.0}
            expected_att = {'days': 16.0, 'hours': 128.0}
            self._assert_worked_days_lines(slip, expected_out, expected_att)

            #  Previous month
            work_entries_prev = version.generate_work_entries(prev_start, prev_end)
            work_entries_prev.action_validate()
            self._assert_no_attendance_in_range(emp, prev_start, prev_end)

            slip_prev = self.env['hr.payslip'].new({
                'name': 'Payslip Nov 2025',
                'employee_id': emp.id,
                'version_id': version.id,
                'company_id': emp.company_id.id,
                'date_from': prev_start,
                'date_to': prev_end,
            })
            expected_out_prev = {'days': 20.0, 'hours': 160.0}
            expected_att_prev = {'days': 0.0, 'hours': 0.0}
            self._assert_worked_days_lines(slip_prev, expected_out_prev, expected_att_prev)

    def test_work_entries_contract_ends_this_month(self):
        """
        Contract ends during current month.
        Checks:
          - current month: Attendance until end, Out-of-contract after end, work entries only for attendance days
          - next month: full Out-of-contract, no work entries
        """
        with freeze_time(date(2025, 12, 20)):
            cal = self.calendar_40h

            month_start, month_end = self._month_bounds(Date.today())
            next_start, next_end = self._month_bounds(Date.today() + relativedelta(months=1))

            contract_start = date(2025, 11, 1)
            contract_end = date(2025, 12, 10)

            emp = self.env['hr.employee'].create({
                'name': 'Jane Doe',
                'company_id': self.company_us.id,
                'department_id': self.dep_rd.id,
                'resource_calendar_id': cal.id,
                'contract_date_start': contract_start,
                'contract_date_end': contract_end,
            })
            version = emp.version_id

            #  Current month
            work_entries = version.generate_work_entries(month_start, month_end)
            work_entries.action_validate()
            self._assert_attendance_in_range(emp, month_start, contract_end, expected_we_number=8.0)
            self._assert_no_attendance_in_range(emp, contract_end + relativedelta(days=1), month_end)

            slip = self.env['hr.payslip'].new({
                'name': 'Payslip Dec 2025 (end contract)',
                'employee_id': emp.id,
                'version_id': version.id,
                'company_id': emp.company_id.id,
                'date_from': month_start,
                'date_to': month_end,
            })
            expected_att = {'days': 8.0, 'hours': 64.0}
            expected_out = {'days': 15.0, 'hours': 120.0}
            self._assert_worked_days_lines(slip, expected_out, expected_att)

            #  Next month
            work_entries_next = version.generate_work_entries(next_start, next_end)
            work_entries_next.action_validate()
            self._assert_no_attendance_in_range(emp, next_start, next_end)

            slip_next = self.env['hr.payslip'].new({
                'name': 'Payslip Jan 2026 (after end contract)',
                'employee_id': emp.id,
                'version_id': version.id,
                'company_id': emp.company_id.id,
                'date_from': next_start,
                'date_to': next_end,
            })
            expected_out_next = {'days': 22.0, 'hours': 176.0}
            expected_att_next = {'days': 0.0, 'hours': 0.0}
            self._assert_worked_days_lines(slip_next, expected_out_next, expected_att_next)
