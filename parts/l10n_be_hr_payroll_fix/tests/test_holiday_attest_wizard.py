# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.tests import tagged, freeze_time
from odoo.addons.l10n_be_hr_payroll.tests.common import TestPayrollCommon


@freeze_time("2026-02-01 08:00:00")
@tagged("post_install_l10n", "post_install", "-at_install")
class TestHolidayAttestWizard(TestPayrollCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        today = date.today()
        legal_leave_work_entry_type = cls.env.ref('hr_work_entry.work_entry_type_legal_leave')
        cls.leave_type_paid = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'requires_allocation': True,
            'request_unit': 'half_day',
            'allocation_validation_type': 'no_validation',
            'work_entry_type_id': legal_leave_work_entry_type.id,
        })

        cls.pfi_employee = cls.env['hr.employee'].create({
            'name': ' Employee',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'contract_type_id': cls.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_pfi').id,
            'start_notice_period': today,
            'end_notice_period': date(2026, 3, 1),
        })

    def test_float_holiday_attest(self):
        """
             Test that the holiday attest of an employee shows the correct allocated leaves and taken leaves in the float format
        """
        today = date.today()

        # Create an allocation of 10.5 days
        allocation = self.env['hr.leave.allocation'].create({
            'name': '10.5 Days Allocation',
            'employee_id': self.pfi_employee.id,
            'holiday_status_id': self.leave_type_paid.id,
            'number_of_days': 10.5,
            'state': 'confirm',
            'date_from': today.replace(day=1, month=1),
            'date_to': today.replace(day=31, month=12),
        })
        allocation._action_validate()

        # Book a leave of 0.5 day
        leave = self.env['hr.leave'].create({
            'name': '10.5 Days Taken',
            'employee_id': self.pfi_employee.id,
            'holiday_status_id': self.leave_type_paid.id,
            'request_date_from': today,
            'request_date_to': today,
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
            'state': 'confirm',
        })
        leave._action_validate()

        # Open the holiday attest wizard
        wizard = self.env['hr.payslip.employee.depature.holiday.attests'].create({
            'employee_id': self.pfi_employee.id,
        })

        time_off_lines = wizard.time_off_line_ids
        self.assertTrue(time_off_lines, "Wizard should have generated time off lines")

        line = time_off_lines.filtered(lambda l: l.leave_type_id == self.leave_type_paid)
        self.assertTrue(line, "Should find a line for 'Paid Time Off Float Test'")

        self.assertEqual(
            line.leave_allocation_count,
            10.5,
            f"Float allocation should be 10.5, got {line.leave_allocation_count}"
        )
        self.assertEqual(
            line.leave_count,
            0.5,
            f"Float leaves should be 0.5, got {line.leave_count}"
        )
