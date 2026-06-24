# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command

from odoo.addons.l10n_mx_hr_payroll.tests.test_payslip_subsidy import TestPayslipSubsidy
from odoo.tests.common import tagged


@tagged("-at_install", "post_install_l10n", "post_install")
class TestPayslipSubsidyEdi(TestPayslipSubsidy):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.richard_emp.write({
            "schedule_pay": "14_days",
            "wage": 5000.0,
        })

    def _assert_subsidy_warning(self, payslip, expected):
        warnings = payslip._get_warnings_by_slip()[payslip]
        has_warning = any("Salary Limit for Employment Subsidy" in (w.get('message') or "") for w in warnings)

        if expected:
            self.assertTrue(has_warning, "Payslip should be flagged for Limit Salary Subsidy exceeded.")
        else:
            self.assertFalse(has_warning, "Payslip incorrectly flagged as Limit Salary Subsidy exceeded.")

    def test_subsidy_warning_exceeded_by_commissions(self):
        payslip_without_commission = self._create_payslip(date(2026, 2, 1))
        payslip_without_commission.action_validate()

        payslip = self._create_payslip(date(2026, 2, 15))
        self._assert_subsidy_warning(payslip, expected=False)

        payslip.input_line_ids = [
                Command.create({
                    "input_type_id": self.env.ref("l10n_mx_hr_payroll.l10n_mx_input_commissions").id,
                    "amount": 2000.0,
                })
            ]
        payslip.compute_sheet()
        self._assert_subsidy_warning(payslip, expected=True)

    def test_subsidy_warning_exceeded_by_wage_increase(self):
        date_from = date(2026, 2, 15)

        self.richard_contract.contract_date_end = date(2026, 2, 14)
        self.richard_emp.create_version({
            "date_version": date_from,
            "contract_date_start": date_from,
            "wage": 7000.0,
        })

        payslip_old = self._create_payslip(date(2026, 2, 1))
        payslip_old.action_validate()

        payslip = self._create_payslip(date_from)
        payslip.compute_sheet()
        self._assert_subsidy_warning(payslip, expected=True)
