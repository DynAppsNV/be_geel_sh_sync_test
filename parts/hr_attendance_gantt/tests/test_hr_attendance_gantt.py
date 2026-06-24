# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tests.common import tagged, TransactionCase
from pytz import utc, timezone


@tagged('-at_install', 'post_install')
class TestHrAttendanceGantt(TransactionCase):
    def test_gantt_progress_bar(self):
        calendar_8 = self.env['resource.calendar'].create({
            'name': 'Calendar 8h',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 17, 'day_period': 'afternoon'}),
            ]
        })

        calendar_10 = self.env['resource.calendar'].create({
            'name': 'Calendar 10h',
            'tz': 'UTC',
            'hours_per_day': 10.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 19, 'day_period': 'afternoon'}),
            ]
        })

        calendar_12 = self.env['resource.calendar'].create({
            'name': 'Calendar 12h',
            'tz': 'UTC',
            'hours_per_day': 12.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 21, 'day_period': 'afternoon'}),
            ]
        })

        contract_emp = self.env['hr.employee'].create({
            'name': "Johhny Contract",
            'date_version': date(2024, 1, 1),
            'contract_date_start': date(2024, 1, 1),
            'wage': 10,
            'resource_calendar_id': calendar_8.id,
        })

        contract_emp.create_version({
            'date_version': date(2024, 2, 1),
            'resource_calendar_id': calendar_10.id,
            'wage': 10,
        })
        contract_emp.create_version({
            'date_version': date(2024, 3, 1),
            'resource_calendar_id': calendar_12.id,
            'wage': 10,
        })

        contract_emp1 = self.env['hr.employee'].create({
            'name': "John Contract",
            'date_version': date(2024, 2, 1),
            'contract_date_start': date(2024, 1, 1),
            'wage': 10,
            'resource_calendar_id': calendar_8.id,
        })

        contract_emp1.create_version({
            'date_version': date(2024, 3, 1),
            'resource_calendar_id': calendar_10.id,
            'wage': 10,
        })
        contract_emp1.create_version({
            'date_version': date(2024, 4, 1),
            'resource_calendar_id': calendar_12.id,
            'wage': 10,
        })

        # First Interval in January
        # should have 8 hours

        interval_1 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                  [contract_emp.id],
                                                                  datetime(2024, 1, 8),
                                                                  datetime(2024, 1, 14))

        self.assertEqual(interval_1[contract_emp.id]['max_value'], 8)

        # Second Interval in January
        # should have 10 hours

        interval_1 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                   [contract_emp.id],
                                                                   datetime(2024, 2, 8),
                                                                   datetime(2024, 2, 14))

        self.assertEqual(interval_1[contract_emp.id]['max_value'], 10)

        # Third Interval in March
        # should have 12 hours

        interval_2 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                  [contract_emp.id],
                                                                  datetime(2024, 3, 4),
                                                                  datetime(2024, 3, 10))

        self.assertEqual(interval_2[contract_emp.id]['max_value'], 12)

        # First Interval in January
        # should have 8 hours

        interval_1 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                  [contract_emp1.id],
                                                                  datetime(2024, 1, 8),
                                                                  datetime(2024, 1, 14))

        self.assertEqual(interval_1[contract_emp1.id]['max_value'], 8)

        # Second Interval in January ending and February starting
        # should have 8 hours

        interval_2 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                  [contract_emp1.id],
                                                                  datetime(2024, 1, 29),
                                                                  datetime(2024, 2, 5))

        self.assertEqual(interval_1[contract_emp1.id]['max_value'], 8)

        # Third Interval in March
        # should have 10 hours

        interval_3 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                   [contract_emp1.id],
                                                                   datetime(2024, 3, 8),
                                                                   datetime(2024, 3, 14))

        self.assertEqual(interval_3[contract_emp1.id]['max_value'], 10)

        # Fourth Interval in April
        # should have 12 hours

        interval_4 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                  [contract_emp1.id],
                                                                  datetime(2024, 4, 4),
                                                                  datetime(2024, 4, 10))

        self.assertEqual(interval_4[contract_emp1.id]['max_value'], 12)

    def test_gantt_progress_with_flexible_employees(self):
        flexible_calendar, calendar = self.env['resource.calendar'].create([
            {
                'name': 'Calendar 8h',
                'tz': 'UTC',
                'company_id': False,
                'full_time_required_hours': 8.0,
                'hours_per_week': 8.0,
                'hours_per_day': 8.0,
                'flexible_hours': True,
            }, {
                'name': 'Calendar 8h',
                'tz': 'UTC',
                'company_id': False,
                'full_time_required_hours': 8.0,
                'hours_per_day': 8.0,
                'hours_per_week': 8.0,
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 17, 'day_period': 'afternoon'}),
                ],
            },
        ])

        emp1, emp2 = self.env['hr.employee'].create([
            {'name': 'freelance1', 'employee_type': 'freelance', 'resource_calendar_id': flexible_calendar.id},
            {'name': 'freelance2', 'employee_type': 'freelance', 'resource_calendar_id': calendar.id},
        ])
        self.assertTrue(emp1.is_flexible)
        self.assertFalse(emp2.is_flexible)
        calendar.flexible_hours = True  # emp2 should now have a flexible hours as well

        interval = self.env['hr.attendance']._gantt_progress_bar(
            'employee_id',
            [emp1.id, emp2.id],
            datetime(2024, 1, 8),
            datetime(2024, 1, 15),
        )

        self.assertEqual(interval[emp1.id]['max_value'], 8)
        self.assertEqual(interval[emp2.id]['max_value'], 8)

        # If the user is not in UTC time, the start and stop datetimes will not at midnight.
        # This could cause issues with the calculation of attendance intervals and, in turn, max_value.
        # This block simulates this case. We'll simulate in Europe/Zurich time

        self.env.user.write({'tz': 'Europe/Zurich'})  # UTC+2 (summer) or UTC+1 (winter)
        interval_non_utc = self.env['hr.attendance']._gantt_progress_bar(
            'employee_id',
            [emp1.id, emp2.id],
            datetime(2024, 1, 7, 22, 0),
            datetime(2024, 1, 14, 22, 0),
        )

        # The max value should be the same, regardless of the browser timezone
        self.assertEqual(interval_non_utc[emp1.id]['max_value'], 8)
        self.assertEqual(interval_non_utc[emp2.id]['max_value'], 8)

    def test_gantt_rows_exclude_archived_amployee(self):
        emp1 = self.env['hr.employee'].create({'name': 'Employee 1'})
        emp2 = self.env['hr.employee'].create({'name': 'Employee 2'})
        gantt_context = {
            'gantt_start_date': '2026-02-10',
            'group_by': ['employee_id'],
            'user_domain': [],
        }
        gantt_domain = [
            '&',
            ['check_in', '<', '2026-02-10 23:00:00'],
            '|',
            '&',
            ['check_in', '<', '2026-02-10 12:00:30'],
            ['check_out', '=', False],
            ['check_out', '>', '2026-02-09 23:00:00']
        ]
        gantt_read_specification = {
            'display_name': {},
            'check_in': {},
            'check_out': {},
            'employee_id': {
            'fields': {
                'display_name': {}
            }
            },
            'color': {},
            'overtime_progress': {}
        }
        self.env['hr.attendance'].create({
            'employee_id': emp1.id,
            'check_in': datetime(2026, 1, 9, 8, 0, 0),
            'check_out': datetime(2026, 1, 9, 17, 0, 0)
        })
        self.env['hr.attendance'].create({
            'employee_id': emp2.id,
            'check_in': datetime(2026, 1, 9, 8, 0, 0),
            'check_out': datetime(2026, 1, 9, 17, 0, 0)
        })
        emp2.active = False
        gaant_data = self.env['hr.attendance'].with_context(**gantt_context).get_gantt_data(
            domain=gantt_domain,
            groupby=['employee_id'],
            read_specification=gantt_read_specification,
            start_date='2026-02-10',
            stop_date='2026-03-10',
            unavailability_fields=['employee_id'],
            scale='day',
        )['groups']
        rows = [employee['employee_id'][0] for employee in gaant_data]
        self.assertIn(emp1.id, rows)
        self.assertNotIn(emp2.id, rows)

    def test_attendance_gantt_unavailabilities_flexible_employee(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'UTC',
            'date_version': date(2019, 1, 1),
            'contract_date_start': date(2019, 1, 1),
        })

        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flex Calendar',
            'tz': 'UTC',
            'flexible_hours': True,
            'hours_per_day': 8,
            'hours_per_week': 40,
            'full_time_required_hours': 40,
            'attendance_ids': [],
        })
        employee.resource_id.calendar_id = flexible_calendar

        unavailabilities = self.env['hr.attendance']._gantt_unavailability(
            'employee_id',
            [employee.id],
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'week',
        )
        self.assertEqual(unavailabilities[employee.id], [])

        public_holiday = self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2019, 1, 5, 0, 0, 0),
            'date_to': datetime(2019, 1, 5, 23, 59, 59),
        })

        unavailabilities = self.env['hr.attendance']._gantt_unavailability(
            'employee_id',
            [employee.id],
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'week',
        )
        self.assertEqual(unavailabilities[employee.id][0]['start'], public_holiday.date_from.astimezone(utc))
        self.assertEqual(unavailabilities[employee.id][0]['stop'], public_holiday.date_to.astimezone(utc))

    def test_gantt_flexible_part_time_schedule(self):
        flexible_calendar = self.env['resource.calendar'].create([
            {
                'name': 'Test Flexible Calendar',
                'tz': 'UTC',
                'company_id': False,
                'full_time_required_hours': 40.0,
                'hours_per_day': 8.0,
                'hours_per_week': 24.0,
                'flexible_hours': True,
            }])
        employee = self.env['hr.employee'].create([{'name': 'Employee Test', 'resource_calendar_id': flexible_calendar.id}])

        interval = self.env['hr.attendance']._gantt_progress_bar(
            'employee_id',
            [employee.id],
            datetime(2024, 1, 8),
            datetime(2024, 1, 15),
        )

        self.assertEqual(interval[employee.id]['max_value'], 24.0)

    def test_attendances_intervals_different_timezones(self):
        """
        Checks that if a flexible schedule has an attendance of 40 hours per week, the expected hours for a week
        stay at 40 hours, even if we change the timezone.
        """
        calendar = self.env['resource.calendar'].sudo().create({
            'company_id': self.env.company.id,
            'name': 'Flexible 40h/week',
            'tz': 'Europe/Brussels',
            'hours_per_day': 8.0,
            'hours_per_week': 40.0,
            'full_time_required_hours': 40.0,
            'flexible_hours': True,
            'schedule_type': 'flexible',
        })
        employee = self.env['hr.employee'].create({
            'name': 'Test',
            'contract_date_start': '2026-02-01',
            'resource_calendar_id': calendar.id,
            'tz': 'America/Recife'
        })
        interval_west = self.env['hr.attendance']._gantt_progress_bar(
            'employee_id',
            [employee.id],
            datetime(2024, 1, 8),
            datetime(2024, 1, 15),
        )
        self.assertAlmostEqual(interval_west[employee.id]['max_value'], 40)
        employee.write({'tz': 'UTC'})
        interval_central = self.env['hr.attendance']._gantt_progress_bar(
            'employee_id',
            [employee.id],
            datetime(2024, 1, 8),
            datetime(2024, 1, 15),
        )
        self.assertAlmostEqual(interval_central[employee.id]['max_value'], 40)
        employee.write({'tz': 'Asia/Pyongyang'})
        interval_east = self.env['hr.attendance']._gantt_progress_bar(
            'employee_id',
            [employee.id],
            datetime(2024, 1, 8),
            datetime(2024, 1, 15),
        )
        self.assertAlmostEqual(interval_east[employee.id]['max_value'], 40)

    def test_time_off_hours_with_flex_schedule_timezone(self):
        """
        Checks that the start and end hours of a time off shown in the attendance calendar taken under a flexible
        schedule with a timezone other than UTC are correct. When the schedule is flexible, the hours from midnight to
        midnight the next day should be grayed out.
        """
        tz = timezone('Europe/Brussels')
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'Europe/Brussels',
            'date_version': date(2019, 1, 1),
            'contract_date_start': date(2019, 1, 1),
        })
        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flex Calendar',
            'tz': 'Europe/Brussels',
            'flexible_hours': True,
            'hours_per_day': 8,
            'full_time_required_hours': 40,
            'attendance_ids': [],
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Time off',
            'resource_id': employee.resource_id.id,
            'date_from': datetime(2019, 1, 5, 8, 0, 0),
            'date_to': datetime(2019, 1, 5, 16, 0, 0),
        })
        employee.resource_id.calendar_id = flexible_calendar
        unavailabilities = self.env['hr.attendance']._gantt_unavailability(
            'employee_id',
            [employee.id],
            tz.localize(datetime(2019, 1, 5, 0, 0)),
            tz.localize(datetime(2019, 1, 5, 23, 59, 59)),
            'day',
        )
        self.assertEqual(unavailabilities[employee.id][0]['start'], datetime(2019, 1, 4, 23, 0).astimezone(utc))
        self.assertEqual(unavailabilities[employee.id][0]['stop'], datetime(2019, 1, 5, 22, 59, 59).astimezone(utc))
