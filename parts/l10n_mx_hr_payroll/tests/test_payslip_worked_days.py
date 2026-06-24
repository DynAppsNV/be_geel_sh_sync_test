# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time

from odoo.fields import Command
from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install_l10n', 'post_install')
class TestPayrollWorkedDays(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mexico = cls.env.ref('base.mx')
        cls.env.company.write({
            'country_id': mexico.id
        })
        cls.richard_emp.write({
            'company_id': cls.env.company.id,
            'country_id': mexico.id,
            'contract_date_end': date(2050, 1, 1),
            'wage': 30000.0,
        })
        cls.richard_contract.structure_id.write({
            'unpaid_work_entry_type_ids': [Command.link(cls.work_entry_type_unpaid.id)],
        })

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Leaves Test',
            'time_type': 'leave',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.work_entry_type_unpaid.id,
            'request_unit': 'hour',
        })
        cls.work_entry_types = {
            entry_type.code: entry_type
            for entry_type in cls.env['hr.work.entry.type'].search([])
        }

    def _create_worked_days(self, name=False, code=False, number_of_days=0, number_of_hours=0):
        return Command.create({
            'name': name,
            'work_entry_type_id': self.work_entry_types[code].id,
            'code': code,
            'number_of_days': number_of_days,
            'number_of_hours': number_of_hours,
        })

    def _create_leave(self, date_from, date_to, hour_from=0.0, hour_to=24.0):
        return self.env['hr.leave'].create({
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'request_hour_from': hour_from,
            'request_hour_to': hour_to,
        })

    def _create_payslip(self, date_from, date_to=None):
        return self.env['hr.payslip'].create({
            'name': 'Payslip Test',
            'employee_id': self.richard_emp.id,
            'date_from': date_from,
            **({'date_to': date_to} if date_to else {})
        })

    def test_monthly_payslip(self):
        payslip = self._create_payslip(date(2030, 1, 1))
        self.assertEqual(payslip._get_paid_amount(), 30000.0)

        self._create_leave(date(2030, 1, 1), date(2030, 1, 15))
        self.assertEqual(payslip._get_paid_amount(), 19000.0)

    def test_hourly_payslip(self):
        self.richard_contract.write({
            'wage_type': 'hourly',
            'hourly_wage': 125.0,
        })
        payslip = self._create_payslip(date(2030, 1, 1))
        self.assertEqual(payslip._get_paid_amount(), 30000.0)

        self._create_leave(date(2030, 1, 1), date(2030, 1, 15))
        self.assertEqual(payslip._get_paid_amount(), 19000.0)

    def test_monthly_payslip_with_partial_leave(self):
        payslip = self._create_payslip(date(2030, 1, 1))
        self.assertEqual(payslip._get_paid_amount(), 30000.0)

        self._create_leave(date(2030, 1, 2), date(2030, 1, 2), 9.0, 11.0)
        self.assertEqual(payslip._get_paid_amount(), 29750.0)

    def test_partial_payslip(self):
        payslip = self._create_payslip(date(2030, 1, 11), date(2030, 1, 21))
        self.assertEqual(payslip._get_paid_amount(), 11000.0)

    def test_partial_payslip_new_hire_month_31_days(self):
        self.richard_contract.contract_date_start = date(2030, 1, 11)
        payslip = self._create_payslip(date(2030, 1, 1))
        self.assertEqual(payslip._get_paid_amount(), 21000.0)

    def test_partial_payslip_new_hire_month_28_days(self):
        self.richard_contract.contract_date_start = date(2030, 2, 11)
        payslip = self._create_payslip(date(2030, 2, 1))
        self.assertEqual(payslip._get_paid_amount(), 18000.0)

    def test_hourly_payslip_by_attendance(self):
        if self.env['ir.module.module']._get('hr_payroll_attendance').state != 'installed':
            self.skipTest("Skipping test because hr_payroll_attendance is not installed.")

        self.richard_contract.write({
            'work_entry_source': 'attendance',
            'wage_type': 'hourly',
            'hourly_wage': 125.0,
        })
        payslip = self._create_payslip(date(2030, 1, 1))

        worked_days_vals = [
            {'name': 'Attendance', 'code': 'WORK100', 'number_of_hours': 88, 'number_of_days': 11},
            {'name': 'Paid Time Off', 'code': 'LEAVE120', 'number_of_hours': 24, 'number_of_days': 3},
        ]
        payslip.write({
            "worked_days_line_ids": [self._create_worked_days(**vals) for vals in worked_days_vals],
        })
        self.assertEqual(payslip._get_paid_amount(), 14000.0)

        worked_days_vals = [
            {'name': 'Unpaid', 'code': 'LEAVE90', 'number_of_hours': 16, 'number_of_days': 2},
            {'name': 'Out of Contract', 'code': 'OUT', 'number_of_hours': 32, 'number_of_days': 4},
        ]
        payslip.write({
            "worked_days_line_ids": [self._create_worked_days(**vals) for vals in worked_days_vals],
        })
        self.assertEqual(payslip._get_paid_amount(), 14000.0)

    @freeze_time('2026-03-10')
    def test_years_worked(self):
        """
        Test the number of years worked by an employee taking gaps between contracts into consideration
        """
        self.richard_contract.contract_date_end = date(2025, 1, 31)
        new_contract_1 = self.richard_emp.create_version({
            'date_version': date(2025, 2, 1),
            'contract_date_start': date(2025, 2, 1),
            'contract_date_end': date(2026, 1, 31),
        })
        new_contract_2 = self.richard_emp.create_version({
            'date_version': date(2026, 3, 1),
            'contract_date_start': date(2026, 3, 1),
        })
        payslip = self._create_payslip(date(2026, 1, 1))

        self.assertEqual(payslip.version_id.id, new_contract_1.id)
        self.assertEqual(payslip.l10n_mx_years_worked, 9)

        payslip = self._create_payslip(date(2026, 3, 1))

        self.assertEqual(payslip.version_id.id, new_contract_2.id)
        self.assertEqual(payslip.l10n_mx_years_worked, 1)

    def test_compute_sheets_with_higher_seniority(self):
        """
        Ensure that computing a payslip for an employee with more than the maximum
        defined years in the holiday table does not raise a KeyError.
        """
        self.richard_emp.write({
            'contract_date_start': '1985-01-01',
            'wage': 100000
        })
        payslip = self._create_payslip(date(2026, 1, 1))
        # This should no longer raise KeyError
        self.assertTrue(payslip.compute_sheet())
