# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, freeze_time


class TestPayrollDashboardInvalidIBANWarning(TransactionCase):

    def setUp(self):
        super().setUp()

        self.invalid_iban_warning = self.env.ref('hr_payroll_account_iso20022.hr_payroll_dashboard_warning_employee_invalid_bank_account')
        bank_partner = self.env['res.partner'].create({
            'name': 'Bank Partner',
        })

        self.invalid_employee = self.env['hr.employee'].create({
            'name': 'Invalid IBAN Employee',
            'company_id': self.env.company.id,
            'contract_date_start': date(year=2026, month=1, day=1),
            'bank_account_ids': [
                Command.create({
                    'bank_name': 'Invalid IBAN Bank',
                    'partner_id': bank_partner.id,
                    'acc_number': '1234567',
                    'allow_out_payment': True,
                }),
            ],
        })
        self.invalid_employee.create_version({
            'date_version': date(year=2025, month=1, day=1),
            'contract_date_start': date(year=2025, month=1, day=1),
            'contract_date_end': date(year=2025, month=12, day=31),
        })
        self.invalid_employee.create_version({
            'date_version': date(year=2026, month=1, day=1),
            'contract_date_start': date(year=2026, month=1, day=1),
            'contract_date_end': date(year=2026, month=12, day=31),
        })

        self.valid_employee = self.env['hr.employee'].create({
            'name': 'Valid IBAN Employee',
            'company_id': self.env.company.id,
            'contract_date_start': date(year=2026, month=1, day=1),
            'bank_account_ids': [
                Command.create({
                    'bank_name': 'Valid IBAN Bank',
                    'partner_id': bank_partner.id,
                    'acc_number': 'BE71096123456769',
                    'allow_out_payment': True,
                }),
            ],
        })
        self.valid_employee.create_version({
            'date_version': date(year=2025, month=1, day=1),
            'contract_date_start': date(year=2025, month=1, day=1),
            'contract_date_end': date(year=2025, month=12, day=31),
        })
        self.valid_employee.create_version({
            'date_version': date(year=2026, month=1, day=1),
            'contract_date_start': date(year=2026, month=1, day=1),
            'contract_date_end': date(year=2026, month=12, day=31),
        })

    @freeze_time('2026-02-01')
    def test_invalid_employees_in_warning(self):
        warnings = self.env['hr.payslip'].get_dashboard_warnings()

        warning_data = next((w for w in warnings if w['string'] == self.invalid_iban_warning.name), None)
        self.assertTrue(warning_data, "There should be a dashboard warning for invalid IBAN employees.")

        employees = self.env['hr.employee'].search(warning_data['action']['domain'])
        self.assertIn(self.invalid_employee, employees, "Employee with invalid IBAN should appear in warning.")
        self.assertNotIn(self.valid_employee, employees, "Employee with valid IBAN should not appear in warning.")

        invalid_employee_id_count = employees.mapped('id').count(self.invalid_employee.id)
        self.assertEqual(invalid_employee_id_count, 1, "Invalid IBAN employee should only be counted once even with multiple versions.")
