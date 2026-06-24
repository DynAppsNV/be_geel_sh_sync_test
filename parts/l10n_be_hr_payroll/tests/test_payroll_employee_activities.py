# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time

from odoo.tests import tagged
from .common import TestPayrollCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPayrollEmployeeActivities(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with freeze_time('2025-01-01'):
            credit_time_work_entry_type = cls.env.ref('hr_work_entry.l10n_be_work_entry_type_credit_time')
            cls.calendar_part_time_credit_time = cls.env['resource.calendar'].create({
            'name': 'Part time credit time 40%',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': credit_time_work_entry_type.id}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'work_entry_type_id': credit_time_work_entry_type.id}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': credit_time_work_entry_type.id}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'work_entry_type_id': credit_time_work_entry_type.id}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': credit_time_work_entry_type.id}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon', 'work_entry_type_id': credit_time_work_entry_type.id}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ]
        })
            cls.employee = cls.create_employee({
                'name': 'Some Dude',
                'date_version': date(2025, 1, 1),
                'contract_date_start': date(2025, 1, 1),
                'contract_date_end': False,
                'resource_calendar_id': cls.calendar_part_time_credit_time.id,
            })
            cls.version = cls.employee.version_id

    def test_only_one_dimona_activity_for_hr_version(self):
        """
        Test that a version only creates a related dimona or part time activity
        if there is none yet.
        """
        employee_domain = [('res_model', '=', 'hr.employee'), ('res_id', '=', self.employee.id)]

        employee_activities = self.env['mail.activity'].search(employee_domain)
        part_time_activities = employee_activities.filtered(lambda a: a.summary == 'Part Time')
        dimona_activities = employee_activities.filtered(lambda a: a.summary == 'Dimona')
        self.assertEqual(len(part_time_activities), 1, 'A part time activity should have been created.')
        self.assertEqual(len(dimona_activities), 1, 'A dimona activity should have been created.')

        self.version._trigger_l10n_be_next_activities()

        employee_activities = self.env['mail.activity'].search(employee_domain)
        part_time_activities = employee_activities.filtered(lambda a: a.summary == 'Part Time')
        dimona_activities = employee_activities.filtered(lambda a: a.summary == 'Dimona')
        self.assertEqual(len(part_time_activities), 1, 'The existing part time activity should prevent the creation of a new one.')
        self.assertEqual(len(dimona_activities), 1, 'The existing dimona activity should prevent the creation of a new one.')

    def test_part_time_activity_for_new_version(self):
        """
        Test that a new part time activity is created for new contracts, even if previous part time contract
        """
        version = self.employee.create_version({
            'date_version': date(2025, 2, 1),
        })

        with freeze_time('2025-02-03'):
            self.employee._cron_update_current_version_id()
            employee_domain = [('res_model', '=', 'hr.employee'), ('res_id', '=', self.employee.id)]

            employee_activities = self.env['mail.activity'].search(employee_domain)
            part_time_activities = employee_activities.filtered(lambda a: a.summary == 'Part Time')
            self.assertEqual(len(part_time_activities), 1, 'Only one part time activity should exist.')

        with freeze_time('2025-03-03'):
            version.write({
                'contract_date_end': date(2025, 2, 28),
            })
            march_version = self.employee.create_version({
                'date_version': date(2025, 3, 1),
                'contract_date_start': date(2025, 3, 1),
                'contract_date_end': False,
            })

            self.employee._cron_update_current_version_id()
            employee_activities = self.env['mail.activity'].search(employee_domain)
            part_time_activities = employee_activities.filtered(lambda a: a.summary == 'Part Time')
            self.assertEqual(len(part_time_activities), 2, 'A second part time activity should have been created for the new contract.')

        with freeze_time('2025-04-01'):
            march_version.write({
                'contract_date_end': date(2025, 4, 2),
            })
            self.employee.create_version({
                'date_version': date(2025, 4, 3),
                'contract_date_start': date(2025, 4, 3),
                'contract_date_end': False,
            })

        with freeze_time('2025-04-04'):
            self.employee._cron_update_current_version_id()
            employee_activities = self.env['mail.activity'].search(employee_domain)
            part_time_activities = employee_activities.filtered(lambda a: a.summary == 'Part Time')
            self.assertEqual(len(part_time_activities), 3, 'A third part time activity should have been created for the new contract.')
