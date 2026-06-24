# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from dateutil.rrule import MONTHLY, rrule
from codecs import BOM_UTF8

from odoo import Command
from odoo.tests import tagged

from .common import TestL10NHkHrPayrollAccountCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSalaryRules(TestL10NHkHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.resource_calendar_20_hours_per_week = cls.resource_calendar.copy({
            'name': "Test Calendar : 20 Hours/Week",
            'hours_per_day': 4,
            'hours_per_week': 20,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Saturday Morning', 'dayofweek': '5', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('hr_work_entry.l10n_hk_work_entry_type_weekend').id}),
                (0, 0, {'name': 'Sunday Morning', 'dayofweek': '6', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('hr_work_entry.l10n_hk_work_entry_type_weekend').id}),
            ]
        })
        cls.env.company.write({
            'l10n_hk_employer_name': 'Odoo S.A.',
            'l10n_hk_employer_file_number': '123-12345678',
        })

    def test_001_a_regular_payslip(self):
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self._validate_worked_days(payslip, {
            'WORK100': (22.0, 176.0, 14193.55),
            'HKLEAVE600': (9.0, 72.0, 5806.45),
        })

        payslip_results = {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'GROSS': 20200.0, 'ERMC': -1010.0, 'NET': 20200.0, 'MEA': 20200.0}
        self._validate_payslip(payslip, payslip_results)

    def test_001_b_moving_daily_wage_computation(self):
        hk_annual_leave_allocation = self.env['hr.leave.allocation'].create({
            'name': 'HK Annual Leave Allocation',
            'holiday_status_id': self.env.ref('hr_holidays.l10n_hk_leave_type_annual_leave').id,
            'number_of_days': 10,
            'employee_id': self.employee.id,
            'state': 'confirm',
            'date_from': '2023-01-01',
        })
        hk_annual_leave_allocation.action_approve()
        leaves_to_create = [
            (datetime(2023, 3, 7), datetime(2023, 3, 7), self.env.ref('hr_holidays.l10n_hk_leave_type_unpaid_leave')),
            (datetime(2023, 4, 11), datetime(2023, 4, 11), self.env.ref('hr_holidays.l10n_hk_leave_type_annual_leave')),
        ]
        for date_from, date_to, leave_type in leaves_to_create:
            self._generate_leave(date_from, date_to, leave_type)
        results = {
            1: {
                'moving_daily_wage': 0,
                'payslip': {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'GROSS': 20200.0, 'ERMC': -1010.0, 'NET': 20200.0, 'MEA': 20200.0}
            },
            2: {
                'moving_daily_wage': 651.61,
                'payslip': {'BASIC': 20000.0, 'COMMISSION': 10000.0, 'ALW.INT': 200.0, '713_GROSS': 30200.0, 'MPF_GROSS': 30200.0, 'GROSS': 30200.0, 'EEMC': -1500.0, 'ERMC': -1500.0, 'NET': 28700.0, 'MEA': 28700.0},
            },
            3: {
                'moving_daily_wage': 854.24,
                'payslip': {'BASIC': 19354.84, 'ALW.INT': 193.55, '713_GROSS': 19548.39, 'MPF_GROSS': 19548.39, 'EEMC': -977.42, 'ERMC': -977.42, 'GROSS': 19548.39, 'NET': 18570.97, 'MEA': 18570.97},
            },
            4: {
                'moving_daily_wage': 785.94,
                'payslip': {'BASIC': 20119.28, 'ALW.INT': 200.0, '713_GROSS': 20319.28, 'MPF_GROSS': 20319.28, 'EEMC': -1015.96, 'ERMC': -1015.96, 'GROSS': 20319.28, 'NET': 19303.32, 'MEA': 19303.32},
            }
        }
        for month in range(1, 5):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})] if month == 2 else False,
            )

            self.assertEqual(len(payslip.worked_days_line_ids), 3 if month in [3, 4] else 2)
            self.assertEqual(len(payslip.input_line_ids), 1 if month == 2 else 0)

            self.assertAlmostEqual(payslip.l10n_hk_average_daily_wage,
                                   results[month]['moving_daily_wage'],
                                   delta=0.01,
                                   msg="Incorrect moving daily wage for the %s month payslip" % month)
            self._validate_payslip(payslip, results[month]['payslip'])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_001_c_maternity_leave_payslip(self):
        leaves_to_create = [
            (datetime(2023, 3, 7), datetime(2023, 3, 13), self.env.ref('hr_holidays.l10n_hk_leave_type_maternity_leave')),
            (datetime(2023, 3, 14), datetime(2023, 4, 11), self.env.ref('hr_holidays.l10n_hk_leave_type_maternity_leave_80')),
        ]
        for date_from, date_to, leave_type in leaves_to_create:
            self._generate_leave(date_from, date_to, leave_type)
        results = {
            3: {'BASIC': 26952.37, 'ALW.INT': 200.0, '713_GROSS': 27152.37, 'MPF_GROSS': 27152.37, 'EEMC': -1357.62, 'ERMC': -1357.62, 'GROSS': 27152.37, 'NET': 25794.75, 'MEA': 25794.75},
            4: {'BASIC': 22158.09, 'ALW.INT': 200.0, '713_GROSS': 22358.09, 'MPF_GROSS': 22358.09, 'EEMC': -1117.9, 'ERMC': -1117.9, 'GROSS': 22358.09, 'NET': 21240.19, 'MEA': 21240.19}
        }
        payslip = self._generate_payslip(
            date(2023, 2, 1),
            date(2023, 2, 28),
            input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})])
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        payslip = self._generate_payslip(date(2023, 3, 1), date(2023, 3, 31))
        self._validate_worked_days(payslip, {
            'HKLEAVE210': (7.0, 56.0, 7549.99),
            'HKLEAVE211': (18.0, 144.0, 15531.41),
        }, skip_lines=True)
        maternity_leave_data = payslip._get_worked_days_line_values(['HKLEAVE211'], ['amount', 'number_of_days'], True)['HKLEAVE211']['sum']
        maternity_leave_daily_wage = maternity_leave_data['amount'] / maternity_leave_data['number_of_days']
        self._validate_payslip(payslip, results[3])
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        payslip = self._generate_payslip(date(2023, 4, 1), date(2023, 4, 30))
        self._validate_worked_days(payslip, {'HKLEAVE211': (11.0, 88.0, 9491.42)}, skip_lines=True)
        maternity_leave_data = payslip._get_worked_days_line_values(['HKLEAVE211'], ['amount', 'number_of_days'], True)['HKLEAVE211']['sum']
        self.assertAlmostEqual(maternity_leave_data['amount'] / maternity_leave_data['number_of_days'], maternity_leave_daily_wage, places=2)
        self._validate_payslip(payslip, results[4])
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

    def test_002_a_credit_time_payslip(self):
        self.contract.write({
            'wage': 10000.0,
            'resource_calendar_id': self.resource_calendar_20_hours_per_week.id,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self._validate_worked_days(payslip, {
            'WORK100': (22.0, 88.0, 7096.77),
            'HKLEAVE600': (9.0, 36.0, 2903.23),
        })

        payslip_results = {'BASIC': 10000.0, 'ALW.INT': 200.0, '713_GROSS': 10200.0, 'MPF_GROSS': 10200.0, 'GROSS': 10200.0, 'ERMC': -510.0, 'NET': 10200.0, 'MEA': 10200.0}
        self._validate_payslip(payslip, payslip_results)

    def test_002_b_credit_time_moving_daily_wage(self):
        self.contract.write({
            'wage': 10000.0,
            'resource_calendar_id': self.resource_calendar_20_hours_per_week.id,
        })

        results = {
            1: {
                'moving_daily_wage': 0,
                'payslip': {'BASIC': 10000.0, 'ALW.INT': 200.0, '713_GROSS': 10200.0, 'MPF_GROSS': 10200.0, 'GROSS': 10200.0, 'ERMC': -510.0, 'NET': 10200.0, 'MEA': 10200.0},
            },
            2: {
                'moving_daily_wage': 329.03,
                'payslip': {'BASIC': 10000.0, 'ALW.INT': 200.0, '713_GROSS': 10200.0, 'MPF_GROSS': 10200.0, 'EEMC': -510.0, 'ERMC': -510.0, 'GROSS': 10200.0, 'NET': 9690.0, 'MEA': 9690.0},
            }
        }

        for month in range(1, 3):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )

            self.assertEqual(len(payslip.worked_days_line_ids), 2)
            self.assertEqual(len(payslip.input_line_ids), 0)

            self.assertAlmostEqual(payslip.l10n_hk_average_daily_wage,
                                   results[month]['moving_daily_wage'],
                                   delta=0.01,
                                   msg="Incorrect moving daily wage for the %s month payslip" % month)
            self._validate_payslip(payslip, results[month]['payslip'])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_003_internet_allowance(self):
        self.contract.write({
            'date_version': date(2023, 1, 10),
            'contract_date_start': date(2023, 1, 10),
        })
        self._generate_leave(
            datetime(2023, 1, 18),
            datetime(2023, 1, 20),
            self.env.ref('hr_holidays.l10n_hk_leave_type_unpaid_leave'))
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self._validate_worked_days(payslip, {
            'WORK100': (13.0, 104.0, 8387.1),
            'LEAVE90': (3.0, 24.0, 0.0),
            'HKLEAVE600': (6.0, 48.0, 3870.97),
            'OUT': (9.0, 72.0, 0.0),
        })

        payslip_results = {'BASIC': 12258.07, 'ALW.INT': 122.58, '713_GROSS': 12380.65, 'MPF_GROSS': 12380.65, 'GROSS': 12380.65, 'ERMC': -619.03, 'NET': 12380.65, 'MEA': 12380.65}
        self._validate_payslip(payslip, payslip_results)

    def test_004_a_mpf_computation(self):
        payslip_results = {
            1: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'GROSS': 20200.0, 'ERMC': -1010.0, 'NET': 20200.0, 'MEA': 20200.0},
            2: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'EEMC': -1010.0, 'ERMC': -1010.0, 'GROSS': 20200.0, 'NET': 19190.0, 'MEA': 19190.0},
            3: {'BASIC': 20000.0, 'COMMISSION': 10000.0, 'ALW.INT': 200.0, '713_GROSS': 30200.0, 'MPF_GROSS': 30200.0, 'EEMC': -1500.0, 'ERMC': -1500.0, 'GROSS': 30200.0, 'NET': 28700.0, 'MEA': 28700.0},
        }
        for month in range(1, 4):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})] if month == 3 else False,
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_b_mpf_first_contribution(self):
        self.contract.write({
            'date_version': date(2023, 2, 1),
            'contract_date_start': date(2023, 2, 1),
        })
        payslip_results = {
            2: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'GROSS': 20200.0, 'ERMC': -1010.0, 'NET': 20200.0, 'MEA': 20200.0},
            3: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'GROSS': 20200.0, 'ERMC': -1010.0, 'NET': 20200.0, 'MEA': 20200.0},
            4: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'EEMC': -1010.0, 'ERMC': -1010.0, 'GROSS': 20200.0, 'NET': 19190.0, 'MEA': 19190.0},
            5: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'EEMC': -1010.0, 'ERMC': -1010.0, 'GROSS': 20200.0, 'NET': 19190.0, 'MEA': 19190.0},
        }
        for month in range(2, 6):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_c_mpf_volunteer_contribution_fixed(self):
        self.contract.write({
            'wage': 21000.0,
            'l10n_hk_internet': 0.0,
            "l10n_hk_member_class_id": self.member_class.id,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip.action_payslip_done()
        payslip.action_payslip_paid()
        self.employee.l10n_hk_member_class_ct_eevc_id.contribution_option = 'percentage'
        inputs = {
            2: {
                'wage': 21000.0,
                'commission': 0.0,
                'vc_percentage': 5,
            },
            3: {
                'wage': 21000.0,
                'commission': 0.0,
                'vc_percentage': 5,
            },
            4: {
                'wage': 32000.0,
                'commission': 0.0,
                'vc_percentage': 5,
            },
            5: {
                'wage': 22000.0,
                'commission': 0.0,
                'vc_percentage': 3,
            },
            6: {
                'wage': 22000.0,
                'commission': 13000.0,
                'vc_percentage': 3,
            },
        }
        payslip_results = {
            2: {'BASIC': 21000.0, '713_GROSS': 21000.0, 'MPF_GROSS': 21000.0, 'EEMC': -1050.0, 'ERMC': -1050.0, 'EEVC': -1050.0, 'ERVC': -1050.0, 'GROSS': 21000.0, 'NET': 18900.0, 'MEA': 18900.0},
            3: {'BASIC': 21000.0, '713_GROSS': 21000.0, 'MPF_GROSS': 21000.0, 'EEMC': -1050.0, 'ERMC': -1050.0, 'EEVC': -1050.0, 'ERVC': -1050.0, 'GROSS': 21000.0, 'NET': 18900.0, 'MEA': 18900.0},
            4: {'BASIC': 32000.0, '713_GROSS': 32000.0, 'MPF_GROSS': 32000.0, 'EEMC': -1500.0, 'ERMC': -1500.0, 'EEVC': -1600.0, 'ERVC': -1600.0, 'GROSS': 32000.0, 'NET': 28900.0, 'MEA': 28900.0},
            5: {'BASIC': 22000.0, '713_GROSS': 22000.0, 'MPF_GROSS': 22000.0, 'EEMC': -1100.0, 'ERMC': -1100.0, 'EEVC': -660.0, 'ERVC': -660.0, 'GROSS': 22000.0, 'NET': 20240.0, 'MEA': 20240.0},
            6: {'BASIC': 22000.0, 'COMMISSION': 13000.0, '713_GROSS': 35000.0, 'MPF_GROSS': 35000.0, 'EEMC': -1500.0, 'ERMC': -1500.0, 'EEVC': -1050.0, 'ERVC': -1050.0, 'GROSS': 35000.0, 'NET': 32450.0, 'MEA': 32450.0}
        }
        for month in range(2, 7):
            self.employee.l10n_hk_member_class_ct_eevc_id.amount = inputs[month]['vc_percentage']
            self.contract.write({'wage': inputs[month]['wage']})
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': inputs[month]['commission']})] if inputs[month]['commission'] else False,
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_d_mpf_volunteer_contribution_cap(self):
        self.contract.write({
            'wage': 21000.0,
            'l10n_hk_internet': 0.0,
            "l10n_hk_member_class_id": self.member_class.id,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip.action_payslip_done()
        payslip.action_payslip_paid()
        inputs = {
            2: {
                'wage': 21000.0,
                'commission': 0.0
            },
            3: {
                'wage': 21000.0,
                'commission': 0.0
            },
            4: {
                'wage': 32000.0,
                'commission': 0.0
            },
            5: {
                'wage': 22000.0,
                'commission': 0.0
            },
            6: {
                'wage': 22000.0,
                'commission': 13000.0
            },
        }
        payslip_results = {
            2: {'BASIC': 21000.0, '713_GROSS': 21000.0, 'MPF_GROSS': 21000.0, 'EEMC': -1050.0, 'ERMC': -1050.0, 'EEVC': 0, 'ERVC': 0, 'GROSS': 21000.0, 'NET': 19950.0, 'MEA': 19950.0},
            3: {'BASIC': 21000.0, '713_GROSS': 21000.0, 'MPF_GROSS': 21000.0, 'EEMC': -1050.0, 'ERMC': -1050.0, 'EEVC': 0, 'ERVC': 0, 'GROSS': 21000.0, 'NET': 19950.0, 'MEA': 19950.0},
            4: {'BASIC': 32000.0, '713_GROSS': 32000.0, 'MPF_GROSS': 32000.0, 'EEMC': -1500.0, 'ERMC': -1500.0, 'EEVC': -100.0, 'ERVC': -100.0, 'GROSS': 32000.0, 'NET': 30400.0, 'MEA': 30400.0},
            5: {'BASIC': 22000.0, '713_GROSS': 22000.0, 'MPF_GROSS': 22000.0, 'EEMC': -1100.0, 'ERMC': -1100.0, 'EEVC': 0, 'ERVC': 0, 'GROSS': 22000.0, 'NET': 20900.0, 'MEA': 20900.0},
            6: {'BASIC': 22000.0, 'COMMISSION': 13000.0, '713_GROSS': 35000.0, 'MPF_GROSS': 35000.0, 'EEMC': -1500.0, 'ERMC': -1500.0, 'EEVC': -250.0, 'ERVC': -250.0, 'GROSS': 35000.0, 'NET': 33250.0, 'MEA': 33250.0},
        }
        for month in range(2, 7):
            self.contract.write({'wage': inputs[month]['wage']})
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': inputs[month]['commission']})] if inputs[month]['commission'] else False,
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_e_mpf_first_contribution_special_case(self):
        self.contract.write({
            'date_version': date(2023, 7, 3),
            'contract_date_start': date(2023, 7, 3),
        })
        payslip_results = {
            7: {'BASIC': 18709.68, 'ALW.INT': 187.1, '713_GROSS': 18896.78, 'MPF_GROSS': 18896.78, 'GROSS': 18896.78, 'ERMC': -944.84, 'NET': 18896.78, 'MEA': 18896.78},
            8: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'ERMC': -1010.0, 'GROSS': 20200.0, 'NET': 20200.0, 'MEA': 20200.0},
            9: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'EEMC': -1010.0, 'ERMC': -1010.0, 'GROSS': 20200.0, 'NET': 19190.0, 'MEA': 19190.0},
            10: {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'MPF_GROSS': 20200.0, 'EEMC': -1010.0, 'ERMC': -1010.0, 'GROSS': 20200.0, 'NET': 19190.0, 'MEA': 19190.0},
        }
        for month in range(7, 11):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_f_mpf_below_mpf_threshold_include_ermc(self):
        self.contract.write({
            'wage': 5000.0,
            'l10n_hk_internet': 0.0,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        payslip_results = {
            2: {'BASIC': 5000.0, '713_GROSS': 5000.0, 'MPF_GROSS': 5000.0, 'ERMC': -250, 'GROSS': 5000.0, 'NET': 5000.0, 'MEA': 5000.0},
            3: {'BASIC': 5000.0, '713_GROSS': 5000.0, 'MPF_GROSS': 5000.0, 'ERMC': -250, 'GROSS': 5000.0, 'NET': 5000.0, 'MEA': 5000.0}
        }

        for month in range(2, 4):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_005_a_end_of_year_payment(self):
        for month in range(1, 12):
            self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            ).action_payslip_done()

        payslip = self._generate_payslip(date(2023, 12, 1), date(2023, 12, 31))
        payslip_results = {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'END_OF_YEAR_PAYMENT': 20235.28, 'MPF_GROSS': 40435.28, 'EEMC': -1500.0, 'ERMC': -1500.0, 'GROSS': 40435.28, 'NET': 38935.28, 'MEA': 38935.28}
        self._validate_payslip(payslip, payslip_results)

    def test_005_b_incomplete_year_end_of_year_payment(self):
        self.contract.write({
            'date_version': date(2023, 7, 3),
            'contract_date_start': date(2023, 7, 3),
        })
        for month in range(7, 12):
            self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            ).action_payslip_done()

        payslip = self._generate_payslip(date(2023, 12, 1), date(2023, 12, 31))
        payslip_results = {'BASIC': 20000.0, 'ALW.INT': 200.0, '713_GROSS': 20200.0, 'END_OF_YEAR_PAYMENT': 10013.69, 'MPF_GROSS': 30213.69, 'EEMC': -1500.0, 'ERMC': -1500.0, 'GROSS': 30213.69, 'NET': 28713.69, 'MEA': 28713.69}
        self._validate_payslip(payslip, payslip_results)

    def test_contract_change(self):
        """
        Test an employee whose contract is updated in the middle of the month.
        The payrun will contain two payslips, and we need to make sure that the amounts of various benefits aren't double.
        """
        self.contract.write({
            'date_version': date(2025, 10, 1),
            'contract_date_start': date(2025, 10, 1),
            'contract_date_end': date(2026, 1, 15),
            'wage': 40000,
            'l10n_hk_mpf_scheme_id': self.mpf_scheme.id,
            "l10n_hk_mpf_contribution_start": "immediate",
            "l10n_hk_mpf_registration_status": "registered",
            "l10n_hk_member_class_id": self.member_class.id,
            "l10n_hk_mpf_scheme_join_date": date(2025, 10, 1),
        })
        self.contract.l10n_hk_member_class_ct_ervc2_id = self.env['l10n_hk.member.class.contribution.type'].create({
            'member_class_id': self.member_class.id,
            'contribution_type': 'employer_2',
            'contribution_option': 'fixed',
            'amount': 200,
        })
        self.employee.create_version({
            'date_version': date(2026, 1, 16),
            'contract_date_start': date(2026, 1, 16),
            'wage': 40000,
        })

        payrun = self.env['hr.payslip.run'].create({
            'date_start': date(2026, 1, 1),
            'date_end': date(2026, 1, 31),
        })
        payrun.generate_payslips(employee_ids=self.employee.ids)
        payslips = payrun.slip_ids.sorted('date_from asc')
        self.assertEqual(len(payslips), 2)
        # Assert the first payslip's line
        first_payslip_results = {
            'BASIC': 19354.84,
            'ALW.INT': 96.77,
            '713_GROSS': 19451.61,
            'MPF_GROSS': 19451.61,
            'EEMC': -972.58,
            'ERMC': -972.58,
            'EEVC': 0.0,
            'ERVC': 0.0,
            'ERVC2': -96.77,
            'GROSS': 19451.61,
            'NET': 18479.03,
            'MEA': 18479.03,
        }
        self._validate_payslip(payslips[0], first_payslip_results)
        # And the second
        second_payslip_results = {
            'BASIC': 20645.16,
            'ALW.INT': 103.23,
            '713_GROSS': 20748.39,
            'MPF_GROSS': 20748.39,
            'EEMC': -527.42,
            'ERMC': -527.42,
            'EEVC': -510.0,
            'ERVC': -510.0,
            'ERVC2': -103.23,
            'GROSS': 20748.39,
            'NET': 19710.97,
            'MEA': 19710.97,
        }
        self._validate_payslip(payslips[1], second_payslip_results)
        # As comparison, we'll also do a payslip for another month of same length.
        date_start = date(2026, 3, 1)
        payrun = self.env['hr.payslip.run'].create({
            'date_start': date_start,
            'date_end': date_start + relativedelta(day=31),
        })
        payrun.generate_payslips(employee_ids=self.employee.ids)
        payslips = payrun.slip_ids
        control_payslip_results = {
            'BASIC': 40000.0,
            'ALW.INT': 200.0,
            '713_GROSS': 40200.0,
            'MPF_GROSS': 40200.0,
            'EEMC': -1500.0,
            'ERMC': -1500.0,
            'EEVC': -510.0,
            'ERVC': -510.0,
            'ERVC2': -200.0,
            'GROSS': 40200.0,
            'NET': 38190.0,
            'MEA': 38190.0,
        }
        self._validate_payslip(payslips, control_payslip_results)
        # And to make sure we're all good, we now sum the two half month payslip and compare the result with the full month one!
        for rule, control_value in control_payslip_results.items():
            self.assertEqual(
                first_payslip_results[rule] + second_payslip_results[rule], control_value
            )

    def test_contract_change_middle_monthly_payrun(self):
        """
        Same as above, but the payslip is between two middle of months.
        """
        self.contract.write({
            'date_version': date(2025, 10, 1),
            'contract_date_start': date(2025, 10, 1),
            'contract_date_end': date(2026, 1, 31),
            'wage': 40000,
        })
        self.employee.create_version({
            'date_version': date(2026, 2, 1),
            'contract_date_start': date(2026, 2, 1),
            'wage': 40000,
        })

        payrun = self.env['hr.payslip.run'].create({
            'date_start': date(2026, 1, 15),
            'date_end': date(2026, 2, 15),
        })
        payrun.generate_payslips(employee_ids=self.employee.ids)
        payslips = payrun.slip_ids.sorted('date_from asc')
        self.assertEqual(len(payslips), 2)
        # Assert the first payslip's line
        first_payslip_results = {
            'BASIC': 21250.0,
            'ALW.INT': 106.25,
            '713_GROSS': 21356.25,
            'MPF_GROSS': 21356.25,
            'EEMC': -1067.81,
            'ERMC': -1067.81,
            'GROSS': 21356.25,
            'NET': 20288.44,
            'MEA': 20288.44,
        }
        self._validate_payslip(payslips[0], first_payslip_results)
        # And the second
        second_payslip_results = {
            'BASIC': 18750.0,
            'ALW.INT': 93.75,
            '713_GROSS': 18843.75,
            'MPF_GROSS': 18843.75,
            'EEMC': -432.19,
            'ERMC': -432.19,
            'GROSS': 18843.75,
            'NET': 18411.56,
            'MEA': 18411.56,
        }
        self._validate_payslip(payslips[1], second_payslip_results)
        # As comparison, we'll also do a payslip for another month of same length.
        date_start = date(2026, 3, 1)
        payrun = self.env['hr.payslip.run'].create({
            'date_start': date_start,
            'date_end': date_start + relativedelta(day=31),
        })
        payrun.generate_payslips(employee_ids=self.employee.ids)
        payslips = payrun.slip_ids
        control_payslip_results = {
            'BASIC': 40000.0,
            'ALW.INT': 200.0,
            '713_GROSS': 40200.0,
            'MPF_GROSS': 40200.0,
            'EEMC': -1500.0,
            'ERMC': -1500.0,
            'GROSS': 40200.0,
            'NET': 38700.0,
            'MEA': 38700.0,
        }
        self._validate_payslip(payslips, control_payslip_results)
        # And to make sure we're all good, we now sum the two half month payslip and compare the result with the full month one!
        for rule, control_value in control_payslip_results.items():
            self.assertEqual(
                first_payslip_results[rule] + second_payslip_results[rule], control_value
            )

    def test_contract_change_rent(self):
        """
        Test the case of a contract change where rent is involved.
        In this scenario, the half month wage shouldn't be enough to cover the whole rent amount; but we expect the two
        halves to make up for the whole amount.
        """
        self.contract.write({
            'date_version': date(2025, 10, 1),
            'contract_date_start': date(2025, 10, 1),
            'contract_date_end': date(2026, 1, 15),
            'wage': 40000,
        })
        self.env['l10n_hk.rental'].create({
            'name': 'test rental',
            'address': 'test address',
            'nature': 'flat',
            'state': 'open',
            'amount': 25000,
            'date_start': date(2025, 1, 1),
            'employee_id': self.employee.id,
        })
        self.employee.create_version({
            'date_version': date(2026, 1, 16),
            'contract_date_start': date(2026, 1, 16),
            'wage': 40000,
        })

        payrun = self.env['hr.payslip.run'].create({
            'date_start': date(2026, 1, 1),
            'date_end': date(2026, 1, 31),
        })
        payrun.generate_payslips(employee_ids=self.employee.ids)
        payslips = payrun.slip_ids.sorted('date_from asc')
        self.assertEqual(len(payslips), 2)
        # Assert the first payslip's line
        first_payslip_results = {
            'HRA': 19354.84,
            'BASIC': 0.0,
            'ALW.INT': 96.77,
            '713_GROSS': 19451.61,
            'MPF_GROSS': 19451.61,
            'EEMC': -972.58,
            'ERMC': -972.58,
            'GROSS': 19451.61,
            'NET': 18479.03,
            'MEA': 18479.03,
        }
        self._validate_payslip(payslips[0], first_payslip_results)
        # And the second
        second_payslip_results = {
            'HRA': 5645.16,
            'BASIC': 15000.0,
            'ALW.INT': 103.23,
            '713_GROSS': 20748.39,
            'MPF_GROSS': 20748.39,
            'EEMC': -527.42,
            'ERMC': -527.42,
            'GROSS': 20748.39,
            'NET': 20220.97,
            'MEA': 20220.97,
        }
        self._validate_payslip(payslips[1], second_payslip_results)
        # As comparison, we'll also do a payslip for another month of same length.
        date_start = date(2026, 3, 1)
        payrun = self.env['hr.payslip.run'].create({
            'date_start': date_start,
            'date_end': date_start + relativedelta(day=31),
        })
        payrun.generate_payslips(employee_ids=self.employee.ids)
        payslips = payrun.slip_ids
        control_payslip_results = {
            'HRA': 25000.0,
            'BASIC': 15000.0,
            'ALW.INT': 200.0,
            '713_GROSS': 40200.0,
            'MPF_GROSS': 40200.0,
            'EEMC': -1500.0,
            'ERMC': -1500.0,
            'GROSS': 40200.0,
            'NET': 38700.0,
            'MEA': 38700.0,
        }
        self._validate_payslip(payslips, control_payslip_results)
        # And to make sure we're all good, we now sum the two half month payslip and compare the result with the full month one!
        for rule, control_value in control_payslip_results.items():
            self.assertEqual(
                first_payslip_results[rule] + second_payslip_results[rule], control_value
            )

    def test_sick_leaves_over_rest_days(self):
        """ Validate that a sick leave doesn't take precedence over a rest day. """
        date_start = date(2025, 1, 1)
        self.contract.write({
            'date_version': date_start,
            'contract_date_start': date_start,
        })

        self._generate_leave(date(2025, 10, 3), date(2025, 10, 7), self.env.ref('hr_holidays.l10n_hk_leave_type_sick_leave_80'))
        payslip = self._generate_payslip(date(2025, 10, 1), date(2025, 10, 31))
        # In the 31 days of October 2025 we have:
        # 20 work days (1-2, 8-10, 13-17, 20-24, 27-31)
        # 8 weekend days (4-5, 11-12, 18-19, 25-26)
        # 3 sick leave day (3, 6-7). The sick leave on the 4-5 are no taking precedence over the weekend work entry.
        self._validate_worked_days(payslip, {
            'HKLEAVE111': (3.0, 24.0, 0.0),  # ADW is zero due to no previous payslips, but this doesn't affect the test.
            'HKLEAVE600': (8.0, 64.0, 5161.29),
            'WORK100': (20.0, 160.0, 12903.23),
        })

    def test_global_reimbursement_and_deduction(self):
        """Test whether GLOBAL_REIMBURSEMENT and GLOBAL_DEDUCTION are computed correctly and flow into IR56 AmtOfSalary."""
        self.employee.write({
            'l10n_hk_surname': 'Employee',
            'l10n_hk_given_name': 'Test',
            'sex': 'male',
            'identification_id': 'A123456(0)',
            'private_street': '1 Test Street',
            'private_city': 'Hong Kong',
            'private_state_id': self.env.ref('base.state_hk_hk').id,
            'private_country_id': self.env.ref('base.hk').id,
        })

        payslip = self._generate_payslip(
            date(2026, 1, 1),
            date(2026, 1, 31),
            input_line_ids=[
                Command.create({'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_global_reimbursement').id, 'amount': 1000.0}),
                Command.create({'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_global_deduction').id, 'amount': 500.0}),
            ],
        )
        self._validate_payslip(payslip, {
            'BASIC': 20000.0,
            'ALW.INT': 200.0,
            'GLOBAL_REIMBURSEMENT': 1000.0,
            'GLOBAL_DEDUCTION': -500.0,
            '713_GROSS': 20700.0,
            'MPF_GROSS': 20700.0,
            'EEMC': -1035.0,
            'ERMC': -1035.0,
            'GROSS': 21200.0,
            'NET': 19665.0,
            'MEA': 19665.0,
        })
        payslip.action_payslip_done()

        ir56b = self.env['l10n_hk.ir56b'].create({
            'start_year': 2025,
            'start_month': '4',
            'end_year': 2026,
            'end_month': '3',
            'name_of_signer': 'Test Signer',
            'designation_of_signer': 'Manager',
            'type_of_form': 'O',
        })
        data = ir56b._get_rendering_data(self.employee)
        self.assertNotIn('error', data, data.get('error'))
        self.assertEqual(data['employees_data'][0]['AmtOfSalary'], 20500)

        self.employee.departure_reason_id = self.env.ref('hr.departure_resigned').id
        ir56f = self.env['l10n_hk.ir56f'].create({
            'start_year': 2025,
            'start_month': '4',
            'end_year': 2026,
            'end_month': '1',
            'name_of_signer': 'Test Signer',
            'designation_of_signer': 'Manager',
            'type_of_form': 'O',
        })
        ir56f.line_ids = [Command.create({
            'employee_id': self.employee.id,
            'res_model': 'l10n_hk.ir56f',
            'res_id': ir56f.id,
        })]
        data = ir56f._get_rendering_data(self.employee)
        self.assertNotIn('error', data, data.get('error'))
        self.assertEqual(data['employees_data'][0]['AmtOfSalary'], 20500)

        ir56g = self.env['l10n_hk.ir56g'].create({
            'start_year': 2025,
            'start_month': '4',
            'end_year': 2026,
            'end_month': '1',
            'name_of_signer': 'Test Signer',
            'designation_of_signer': 'Manager',
            'type_of_form': 'O',
        })
        data = ir56g._get_rendering_data(self.employee)
        self.assertNotIn('error', data, data.get('error'))
        self.assertEqual(data['employees_data'][0]['AmtOfSalary'], 20500)

    def test_ird_export_file_encoding(self):
        """ Validate that we correctly export the files as UTF-8 with BOM, and that the header is correctly capitalized. """
        self.employee.write({
            'name': "Test Employee",
            'l10n_hk_surname': 'NATALIE',
            'l10n_hk_given_name': 'CHAN',
            'identification_id': 'Z1234567',
            'private_street': 'Another Address Line',
            'private_state_id': self.env.ref('base.state_hk_hk').id,
            'sex': 'female',
            'marital': 'married',
            'job_title': 'Experience Developer',
            'spouse_complete_name': 'AU-YEUNG FUNG',
            'l10n_hk_spouse_identification_id': 'Z683365A',
        })

        payruns_data = []
        for dt in rrule(MONTHLY, dtstart=date(2024, 4, 1), until=date(2025, 3, 31)):
            payruns_data.append({
                'date_start': dt,
                'date_end': dt + relativedelta(day=31),
                'structure_id': self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id,
            })
        payruns = self.env['hr.payslip.run'].create(payruns_data)
        for payrun in payruns:
            payrun.generate_payslips(employee_ids=self.employee.ids)
        payruns.action_validate()
        payruns.action_paid()

        ir56b = self.env['l10n_hk.ir56b'].create({
            'start_year': '2024',
            'start_month': '4',
            'end_year': '2025',
            'end_month': '3',
            'year_of_employer_return': '2025',
            'name_of_signer': 'Marc Admin',
            'designation_of_signer': 'Mr.',
        })
        ir56b.action_generate_declarations()
        ir56b.action_generate_xml()
        self.assertTrue(bool(ir56b.xml_file), 'The IRD reports were successfully generated.')
        xml_bytes = base64.decodebytes(ir56b.xml_file)
        self.assertTrue(
            xml_bytes.startswith(BOM_UTF8),
            "The UTF-8 BOM is missing!",
        )
        expected_header = b'<?xml version=\'1.0\' encoding=\'UTF-8\''
        self.assertTrue(
            xml_bytes[3:].startswith(expected_header),
            "Header mismatch or incorrect capitalization after the BOM.",
        )
