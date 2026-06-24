# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.fields import Date

from odoo.addons.hr_payroll.tests.common import TestPayslipBase


class TestPayrun(TestPayslipBase):

    def test_payrun_archived_employee(self):
        """
        When creating a payrun, it should filter to keep only versions of active employees.
        """
        emp_active = self.env['hr.employee'].create({
            'name': 'Active',
            'active': True,
            'company_id': self.company_us.id,
            'contract_date_start': '2026-03-01',
        })
        emp_archived = self.env['hr.employee'].create({
            'name': 'Archived',
            'active': False,
            'company_id': self.company_us.id,
            'contract_date_start': '2026-03-01',
        })

        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': '2026-03-01',
            'date_end': '2026-03-31',
            'name': 'Payrun'
        })
        version_ids = payslip_run._get_valid_version_ids()
        self.assertIn(emp_active.version_id.id, version_ids)
        self.assertNotIn(emp_archived.version_id.id, version_ids)

    def test_payslip_semi_monthly_dates(self):
        with freeze_time('2023-01-12'):
            payslip_run = self.env['hr.payslip.run'].create({
                'name': 'Payrun',
            })
            payslip_run.schedule_pay = 'semi-monthly'
            self.assertEqual(payslip_run.date_start, Date.to_date('2023-01-01'))
            self.assertEqual(payslip_run.date_end, Date.to_date('2023-01-15'))
        with freeze_time('2023-01-20'):
            payslip_run = self.env['hr.payslip.run'].create({
                'name': 'Payrun',
            })
            payslip_run.schedule_pay = 'semi-monthly'
            self.assertEqual(payslip_run.date_start, Date.to_date('2023-01-16'))
            self.assertEqual(payslip_run.date_end, Date.to_date('2023-01-31'))
