# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.tests.common import tagged


@tagged("-at_install", "post_install_l10n", "post_install")
class TestPayslipSubsidy(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mexico = cls.env.ref("base.mx")
        cls.env.company.country_id = mexico.id
        cls.richard_emp.write({
            "company_id": cls.env.company,
            "country_id": mexico.id,
        })
        cls.base_date_complete = date(2026, 5, 1)
        cls.base_date_overlapping = date(2026, 4, 29)

    def _create_payslip(self, date_from):
        return self.env["hr.payslip"].create({
            "name": "Payslip Test",
            "employee_id": self.richard_emp.id,
            "date_from": date_from,
        })

    def _assert_subsidy_values(self, date_from, expected_current_month, expected_next_month=0.0):
        payslip = self._create_payslip(date_from)
        payslip.action_validate()
        line_values = {line.code: line.total for line in payslip.line_ids}

        self.assertAlmostEqual(line_values.get("SUBSIDY_CURRENT_MONTH", 0.0), expected_current_month)
        self.assertAlmostEqual(line_values.get("SUBSIDY_NEXT_MONTH", 0.0), expected_next_month)
        self.assertAlmostEqual(line_values.get("SUBSIDY", 0.0), expected_current_month + expected_next_month)

    def _assert_complete_period(self, schedule_pay, wage, expected_current_month, expected_next_month=0.0):
        self.richard_emp.schedule_pay = schedule_pay
        self.richard_emp.wage = wage
        self._assert_subsidy_values(self.base_date_complete, expected_current_month, expected_next_month)

    def _assert_overlapping_period(self, schedule_pay, wage, first_payslip, mid_payslips, last_payslip):
        self.richard_emp.schedule_pay = schedule_pay
        self.richard_emp.wage = wage
        date_from = self.base_date_overlapping
        period_delta = self.env["hr.payslip"]._schedule_timedelta(schedule_pay, date_from, "MX") + relativedelta(days=1)

        with self.subTest(msg=f"Overlapping {schedule_pay}: First split payslip"):
            self._assert_subsidy_values(date_from, *first_payslip)
            date_from += period_delta

        mid_count, mid_subsidy = mid_payslips
        for _ in range(mid_count):
            with self.subTest(msg=f"Overlapping {schedule_pay}: Standard payslip"):
                self._assert_subsidy_values(date_from, mid_subsidy)
                date_from += period_delta

        with self.subTest(msg=f"Overlapping {schedule_pay}: Final split accumulative payslip"):
            self._assert_subsidy_values(date_from, *last_payslip)

    def test_subsidy_bimonthly(self):
        self._assert_complete_period("bi-monthly", 22985.33, 0.0)
        self._assert_complete_period("bi-monthly", 22985.32, 535.65, 535.65)

    def test_subsidy_monthly(self):
        self._assert_complete_period("monthly", 11492.67, 0.0)
        self._assert_complete_period("monthly", 11492.66, 535.65)

    def test_subsidy_biweekly(self):
        self._assert_complete_period("bi-weekly", 5746.34, 0.0)
        self._assert_complete_period("bi-weekly", 5746.33, 267.82)

    def test_subsidy_14_days(self):
        self._assert_overlapping_period("14_days", 5292.68, (0.0, 0.0), (1, 0.0), (0.0, 0.0))
        self._assert_overlapping_period("14_days", 5292.67, (35.24, 211.44), (1, 246.68), (77.53, 158.58))

    def test_subsidy_10_days(self):
        self._assert_overlapping_period("10_days", 3780.49, (0.0, 0.0), (2, 0.0), (0.0, 0.0))
        self._assert_overlapping_period("10_days", 3780.48, (35.24, 140.96), (2, 176.20), (42.29, 123.34))

    def test_subsidy_weekly(self):
        self._assert_overlapping_period("weekly", 2646.34, (0.0, 0.0), (3, 0.0), (0.0, 0.0))
        self._assert_overlapping_period("weekly", 2646.33, (35.24, 88.10), (3, 123.34), (77.53, 35.24))

    def test_subsidy_across_years_bimonthly(self):
        self.base_date_complete = date(2025, 12, 1)
        self._assert_complete_period("bi-monthly", 20342.01, 0.0, 536.22)
        self._assert_complete_period("bi-monthly", 20342.0, 474.65, 536.22)

    def test_subsidy_across_years_14_days(self):
        date_from = date(2025, 12, 25)
        self.richard_emp.schedule_pay = "14_days"
        self.richard_emp.wage = 4684.02
        self._assert_subsidy_values(date_from, 0.0, 123.47)
        self.richard_emp.wage = 4684.01
        self._assert_subsidy_values(date_from, 109.29, 123.47)
