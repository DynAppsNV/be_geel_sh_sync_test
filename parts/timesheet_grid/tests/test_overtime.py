# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestOvertime(HttpCase):
    def test_flexible_overtime_positive_utc_offset(self):
        """ Overtime for flexible schedules must not be inflated by timezone offset """
        calendar = self.env['resource.calendar'].create({
            'name': 'Flexible 20h',
            'tz': 'Europe/Brussels',
            'flexible_hours': True,
            'hours_per_day': 4.0,
            'hours_per_week': 20.0,
            'full_time_required_hours': 20.0,
        })

        employee = self.env['hr.employee'].create({
            'name': 'Brussels Employee',
            'resource_calendar_id': calendar.id,
            'employee_type': 'freelance',
            'tz': 'Europe/Brussels',
        })

        result = employee.get_timesheet_and_working_hours_for_employees('2021-03-29', '2021-04-04')
        self.assertEqual(result[employee.id]['units_to_work'], 20.0)
