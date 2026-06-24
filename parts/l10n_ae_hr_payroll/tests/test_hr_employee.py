# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch
from datetime import date

from odoo.fields import Command
from odoo.tests import common, tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestHrEmployee(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_worked_years(self):
        employee_1 = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
            'contract_date_start': date(2023, 2, 15),
            'date_version': date(2023, 2, 15),
            'wage': 15_000.0,
        })

        departure_notice_1 = self.env['hr.departure.wizard'].create({
            'employee_ids':  [Command.link(employee_1.id)],
            'departure_date': date(2025, 2, 14),
            'departure_description': 'foo',
        })
        departure_notice_1.with_context(toggle_active=True).action_register_departure()

        self.assertAlmostEqual(employee_1._l10n_ae_get_worked_years(), 2, 2, "This employee has worked for 2 years")

    def test_compute_l10n_ae_annual_leave_days_without_employee(self):
        employee = self.env['hr.employee'].browse([])
        with patch.object(self.env.cr, 'execute') as mock_execute:
            employee._compute_l10n_ae_annual_leave_days()
            mock_execute.assert_not_called()

    def test_compute_l10n_ae_annual_leave_days_with_annual_leave_allocation(self):
        employee_1 = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
            'contract_date_start': date(2026, 1, 1),
            'date_version': date(2026, 1, 1),
            'wage': 15_000.0,
        })

        annual_leave_type = self.env['hr.leave.type'].create({
            'name': 'Annual test leave type',
            'request_unit': 'day',
            'l10n_ae_is_annual_leave': True
        })

        annual_allocation = self.env['hr.leave.allocation'].create({
            'name': '10 Days Annual Allocation',
            'holiday_status_id': annual_leave_type.id,
            'employee_id': employee_1.id,
            'date_from': date(2026, 1, 1),
            'number_of_days': 10,
            'state': 'confirm'
        })
        annual_allocation._action_validate()

        employee_1._compute_l10n_ae_annual_leave_days()
        self.assertEqual(employee_1.l10n_ae_annual_leave_days_total, 10)

    def test_compute_l10n_ae_annual_leave_days_without_annual_leave_allocation(self):
        employee_1 = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
            'contract_date_start': date(2026, 1, 1),
            'date_version': date(2026, 1, 1),
            'wage': 15_000.0,
        })

        annual_leave_type = self.env['hr.leave.type'].create({
            'name': 'Annual test leave type',
            'request_unit': 'day',
        })

        annual_allocation = self.env['hr.leave.allocation'].create({
            'name': '10 Days Annual Allocation',
            'holiday_status_id': annual_leave_type.id,
            'employee_id': employee_1.id,
            'date_from': date(2026, 1, 1),
            'number_of_days': 10,
            'state': 'confirm',
        })
        annual_allocation._action_validate()

        employee_1._compute_l10n_ae_annual_leave_days()
        self.assertEqual(employee_1.l10n_ae_annual_leave_days_total, 0)
