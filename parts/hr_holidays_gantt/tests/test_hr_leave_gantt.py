# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from pytz import UTC

from odoo.addons.hr_holidays.tests.common import TestHolidayContract
from odoo import Command


class TestHrLeaveGantt(TestHolidayContract):

    def test_gantt_view_without_schedule(self):
        """
        Test that the Time Off Gantt view works correctly even
        when an employee contract has no working schedule set.
        """
        # Remove the working schedule (resource calendar) from the employee's contract
        self.contract_cdi.write({
            'date_start': datetime.strptime('2025-01-01', '%Y-%m-%d').date(),
            'date_end': datetime.strptime('2025-12-31', '%Y-%m-%d').date(),
            'resource_calendar_id': None
        })

        # Create a time off for the employee
        start = datetime.strptime('2025-11-11 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2025-11-11 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

        # Get the Gantt overview data for employees's time off data
        start_date = '2025-11-01 00:00:00'
        stop_date = '2025-11-30 00:00:00'
        gantt_domain = [('employee_id.active', '=', True)]
        gantt_data = self.env["hr.leave.report.calendar"].get_gantt_data(
            gantt_domain,
            ["employee_id"],
            {},
            unavailability_fields=["employee_id"],
            start_date=start_date,
            stop_date=stop_date,
            scale="day",
        )
        group_employee_ids = [group['employee_id'][0] for group in gantt_data['groups']]
        self.assertIn(self.jules_emp.id, group_employee_ids, "The employee should be in the gantt data groups.")

    def test_gantt_view_flex_schedule_time_off_types(self):
        """Checks that the correct areas are grayed out when an employee with a flexible schedule takes days off
        when the type of these days off are either half-days or hours."""

        leave_type_half_day, leave_type_hours = self.env['hr.leave.type'].create([{
            'name': 'Paid Time Off Half',
            'requires_allocation': False,
            'request_unit': 'half_day',
            'allocation_validation_type': 'no_validation',
        }, {
            'name': 'Paid Time Off Hour',
            'requires_allocation': False,
            'request_unit': 'hour',
            'allocation_validation_type': 'no_validation',
        }])
        half_day_leave, hours_leave = self.env['hr.leave'].create([{
            'name': 'Half Day Leave',
            'holiday_status_id': leave_type_half_day.id,
            'employee_id': self.jules_emp.id,
            'request_date_from': datetime(2026, 3, 24),
            'request_date_to': datetime(2026, 3, 24),
            'request_unit_half': True,
            'request_date_from_period': 'am',
            'request_date_to_period': 'am'
        }, {
            'name': 'Hour Leave',
            'holiday_status_id': leave_type_hours.id,
            'employee_id': self.jules_emp.id,
            'request_date_from': datetime(2026, 3, 25),
            'request_date_to': datetime(2026, 3, 25),
            'request_unit_hours': True,
            'request_hour_from': 12.0,
            'request_hour_to': 16.0,
        }])

        flex_schedule = self.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'flexible_hours': True,
            'leave_ids': [
                Command.create({
                    'name': 'half day Leave',
                    'date_from': half_day_leave.request_date_from,
                    'date_to': half_day_leave.request_date_to,
                    'resource_id': self.jules_emp.resource_id.id,
                    'holiday_id': half_day_leave.id
                }),
                Command.create({
                    'name': 'hours Leave',
                    'date_from': hours_leave.request_date_from,
                    'date_to': hours_leave.request_date_to,
                    'resource_id': self.jules_emp.resource_id.id,
                    'holiday_id': hours_leave.id
                })
            ]
        })
        self.jules_emp.write({'resource_calendar_id': flex_schedule.id})
        gantt_domain = [('employee_id.active', '=', True)]
        start_date_half = '2026-03-24 00:00:00'
        stop_date_half = '2026-03-24 23:59:59'

        gantt_data_half = self.env["hr.leave.report.calendar"].get_gantt_data(
            gantt_domain,
            ["employee_id"],
            {},
            unavailability_fields=["employee_id"],
            start_date=start_date_half,
            stop_date=stop_date_half,
            scale="day",
        )
        self.assertEqual(gantt_data_half['unavailabilities']['employee_id'][self.jules_emp.id][0]['start'],
                         datetime(2026, 3, 24, 0, 0, tzinfo=UTC))
        self.assertEqual(gantt_data_half['unavailabilities']['employee_id'][self.jules_emp.id][0]['stop'],
                         datetime(2026, 3, 24, 12, 0, tzinfo=UTC))
        start_date_hour = '2026-03-25 00:00:00'
        stop_date_hour = '2026-03-25 23:59:59'

        gantt_data_hour = self.env["hr.leave.report.calendar"].get_gantt_data(
            gantt_domain,
            ["employee_id"],
            {},
            unavailability_fields=["employee_id"],
            start_date=start_date_hour,
            stop_date=stop_date_hour,
            scale="day",
        )
        self.assertEqual(gantt_data_hour['unavailabilities']['employee_id'][self.jules_emp.id][0]['start'],
                         datetime(2026, 3, 25, 12, 0, tzinfo=UTC))
        self.assertEqual(gantt_data_hour['unavailabilities']['employee_id'][self.jules_emp.id][0]['stop'],
                         datetime(2026, 3, 25, 23, 59, 59, tzinfo=UTC))
