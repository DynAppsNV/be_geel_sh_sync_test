# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import HrWorkEntryAttendanceCommon


@tagged('-at_install', 'post_install', 'work_entry_attendance')
class TestWorkentryAttendance(HrWorkEntryAttendanceCommon):

    def test_basic_generation(self):
        # Create an attendance for each afternoon of september
        attendance_vals_list = []
        for i in range(1, 31):
            new_date = datetime(2021, 9, i, 13, 0, 0)
            if new_date.weekday() >= 5:
                continue
            attendance_vals_list.append({
                'employee_id': self.employee.id,
                'check_in': new_date,
                'check_out': new_date.replace(hour=17),
            })
        attendances = self.env['hr.attendance'].create(attendance_vals_list)
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        # Should not have generated a work entry since no period has been generated yet
        self.assertFalse(work_entries)
        self.contract.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(attendances), len(work_entries))
        self.assertTrue(all(hwe.attendance_id for hwe in work_entries))

    def test_lunch_time_case(self):
        # only consider lunch time for non-flexible attendance based contracts
        week_day = datetime(2022, 9, 19, 8, 0, 0)
        weekend = datetime(2022, 9, 18, 8, 0, 0)
        attendances = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': week_day,
                'check_out': week_day.replace(hour=20),
            },
            {
                'employee_id': self.employee.id,
                'check_in': weekend,
                'check_out': weekend.replace(hour=20),

            }
            ]
        )
        attendances.action_approve_overtime()
        # We should have here 3 work entries in total
        # Sunday -> 08:00 -> 20:00
        # Monday -> 08:00 -> 12:00 and 13:00 -> 20:00
        self.contract.generate_work_entries(date(2022, 9, 18), date(2022, 9, 19))
        sunday = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id),
                                                   ('date', '<', week_day)])

        monday = self.env["hr.work.entry"].search([('employee_id', '=', self.employee.id),
                                                   ('date', '>=', week_day)])

        self.assertEqual(len(sunday), 1)
        self.assertEqual(sunday.date, date(2022, 9, 18))
        self.assertEqual(sunday.duration, 12)

        self.assertEqual(len(monday), 2)
        attendance_type_id = self.env.ref('hr_work_entry.work_entry_type_attendance').id
        overtime_type_id = self.env.ref('hr_work_entry.work_entry_type_overtime').id
        monday_attendance_work_entry = monday.filtered_domain([('work_entry_type_id', '=', attendance_type_id)])
        monday_overtime_work_entry = monday.filtered_domain([('work_entry_type_id', '=', overtime_type_id)])
        self.assertEqual(monday_overtime_work_entry.date, date(2022, 9, 19))
        self.assertEqual(monday_overtime_work_entry.duration, 3)
        self.assertEqual(monday_attendance_work_entry.date, date(2022, 9, 19))
        self.assertEqual(monday_attendance_work_entry.duration, 8)

        # set flexible hours on the employee contract
        self.contract.resource_calendar_id.flexible_hours = True
        flex_day = datetime(2022, 9, 20, 8, 0, 0)
        attendance = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': flex_day,
                'check_out': flex_day.replace(hour=20),
            },
            ]
        )
        attendance.action_approve_overtime()
        # We should have here 1 work entry
        # Tuesday -> 08:00 -> 20:00
        self.contract.generate_work_entries(date(2022, 9, 20), date(2022, 9, 21))
        tuesday = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id),
                                                   ('date', '>=', flex_day)])
        tuesday_attendance_work_entry = tuesday.filtered_domain([('work_entry_type_id', '=', attendance_type_id)])
        tuesday_overtime_work_entry = tuesday.filtered_domain([('work_entry_type_id', '=', overtime_type_id)])
        self.assertEqual(len(tuesday), 2)
        self.assertEqual(tuesday_attendance_work_entry.date, date(2022, 9, 20))
        self.assertEqual(tuesday_attendance_work_entry.duration, 8)
        self.assertEqual(tuesday_overtime_work_entry.date, date(2022, 9, 20))
        self.assertEqual(tuesday_overtime_work_entry.duration, 4)

    def test_timezones(self):
        """ Basic check that timezones do not cause weird behaviors:
            * check that the date range of ``generate_work_entries`` accounts for timezones.
            * check that times are all stored in utc and are not improperly converted
        """
        self.employee.version_id.resource_calendar_id.tz = 'Asia/Tokyo'
        self.employee.tz = 'Asia/Tokyo'
        monday_morning_tokyo = datetime(2024, 10, 20, 22, 0, 0)  # 22:00 sunday utc = 7:00 monday tokyo
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': monday_morning_tokyo,
            'check_out': monday_morning_tokyo.replace(day=21, hour=7),  # 16:00
        })
        self.contract.generate_work_entries(date(2024, 10, 21), date(2024, 10, 21))

        we = self.env["hr.work.entry"].search([
            ('employee_id', '=', self.employee.id),
            ('date', '>=', monday_morning_tokyo)
        ])

        self.assertEqual(len(we), 1)
        self.assertEqual(we.date, date(2024, 10, 21))
        self.assertEqual(we.duration, 8)

    def test_attendance_within_period(self):
        # Tests that an attendance created within an already generated period generates a work entry
        boundaries_attendances = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 1, 14, 0, 0),
                'check_out': datetime(2021, 9, 1, 17, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 30, 14, 0, 0),
                'check_out': datetime(2021, 9, 30, 17, 0, 0),
            },
        ])
        self.contract.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(work_entries), len(boundaries_attendances))

        inner_attendance = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 14, 14, 0, 0),
                'check_out': datetime(2021, 9, 14, 17, 0, 0),
            }
        ])
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(work_entries), len(boundaries_attendances) + len(inner_attendance))

    @freeze_time("2021-09-01")  # to have the timezone in summer time
    def test_attendance_spanning_days(self):
        # Tests that attendances that cross midnight generate work entries that do not cross midnight
        # or conflict. 2 entries for init, 2 for the first attendance, and 4 for the second due to lunch
        self.contract.write({
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
            'resource_calendar_id': False,
        })
        self.env['hr.attendance'].create(
            {
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 10, 22, 0, 0),
            'check_out': datetime(2021, 9, 11, 6, 0, 0),
            }
        )
        self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 11, 22, 0, 0),
                'check_out': datetime(2021, 9, 12, 6, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 13, 22, 0, 0),
                'check_out': datetime(2021, 9, 15, 6, 0, 0),
            },
        ])
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee.id),
            ('active', '=', True),
        ], order='date asc, attendance_id desc')

        self.assertEqual(len(work_entries), 4)
        self.assertEqual(work_entries.mapped('duration'), [8.0, 8.0, 24.0, 8.0])

    def test_unlink(self):
        # Tests that the work entry is archived when unlinking an attendance
        # Makes the attendance create a work entry directly
        self.contract.write({
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 14, 0, 0),
            'check_out': datetime(2021, 9, 14, 17, 0, 0),
        })
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        attendance.unlink()
        self.assertFalse(work_entries.active)

    def test_work_entries_exclude_refused_overtime(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 9, 0),
            'check_out': datetime(2021, 1, 4, 12, 0),
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 13, 0),
            'check_out': datetime(2021, 1, 4, 20, 0),
        })
        attendance.action_refuse_overtime()
        work_entries = self.contract.generate_work_entries(date(2021, 1, 4), date(2021, 1, 4))
        total_work_entry_duration = sum(work_entry.duration for work_entry in work_entries)
        self.assertEqual(total_work_entry_duration, self.employee.resource_calendar_id.hours_per_day)

    def test_fully_flexible_working_schedule_work_entries(self):
        """ Test employee with fully flexible working schedule with attendance as work entry source """
        employee = self.env['hr.employee'].create({
            'name': 'Test',
            'date_version': datetime(2024, 9, 1),
            'contract_date_start': datetime(2024, 9, 1),
            'contract_date_end': datetime(2024, 9, 30),
            'wage': 5000.0,
            'work_entry_source': 'attendance',
            'resource_calendar_id': False,
            'ruleset_id': False,
        })

        self.env['resource.calendar.leaves'].sudo().create({
            'resource_id': employee.resource_id.id,
            'date_from': datetime(2024, 9, 2),
            'date_to': datetime(2024, 9, 3)
        })

        employee.generate_work_entries(datetime(2024, 9, 1), datetime(2024, 9, 30))
        result_entries = self.env['hr.work.entry'].search([('employee_id', '=', employee.id)])
        self.assertEqual(len(result_entries), 2, 'Two work entries should be generated')

        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': datetime(2024, 9, 14, 14, 0, 0),
            'check_out': datetime(2024, 9, 14, 17, 0, 0),
        })
        employee.generate_work_entries(datetime(2024, 9, 1), datetime(2024, 9, 30))
        result_entries = self.env['hr.work.entry'].search([('employee_id', '=', employee.id)])
        self.assertEqual(len(result_entries), 3, 'Two work entry should be generated')

    def test_gto_flexible_calendar(self):
        """
        Test when having a public time off and a flexible user has two
        separate attendances in this day what will be the duration of the
        holiday work entries.
        """
        start = datetime(2018, 1, 1, 6, 0, 0)
        end = datetime(2018, 1, 1, 18, 0, 0)
        self.env['resource.calendar.leaves'].create({
            'date_from': start,
            'date_to': end,
            'work_entry_type_id': self.work_entry_type_leave.id,
        })

        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'flexible calendar',
            'flexible_hours': True,
            'full_time_required_hours': 40,
            'hours_per_day': 8,
            'hours_per_week': 40,
        })

        self.richard_emp.version_id.write({
            'resource_calendar_id': flexible_calendar.id,
            'work_entry_source': 'attendance',
        })

        self.env['hr.attendance'].create([
            {
                'check_in': datetime(2018, 1, 1, 9, 0, 0),
                'check_out': datetime(2018, 1, 1, 11, 0, 0),
                'employee_id': self.richard_emp.id,
            },
            {
                'check_in': datetime(2018, 1, 1, 13, 0, 0),
                'check_out': datetime(2018, 1, 1, 15, 0, 0),
                'employee_id': self.richard_emp.id,
            }
        ])

        work_entries = self.richard_emp.version_ids.generate_work_entries(start.date(), end.date())
        time_off_entries = work_entries.filtered(lambda entry: entry.code == 'LEAVETEST100')
        # Since we are now merging similar work entries on the same day
        # we are going to have only one leave entry
        self.assertEqual(len(time_off_entries), 1)
        self.assertEqual(time_off_entries.duration, 8)
        self.assertEqual((work_entries - time_off_entries).duration, 4)

    def test_worked_time_leave_over_public_holiday(self):
        """Worked-time leaves should not duplicate overlapping public holidays."""
        if 'hr.leave' not in self.env.registry:
            self.skipTest("hr_work_entry_holidays is required to test approved time off work entries")

        self.employee.resource_calendar_id.tz = 'UTC'
        self.employee.resource_calendar_id.flexible_hours = True
        worked_time_type = self.env['hr.work.entry.type'].create({
            'name': 'Worked Time Off',
            'is_leave': True,
            'code': 'WORKEDTIMEOFF',
        })
        leave_type = self.env['hr.leave.type'].create({  # noqa: OLS03001
            'name': 'Worked Time Leave',
            'time_type': 'other',
            'requires_allocation': False,
            'work_entry_type_id': worked_time_type.id,
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'date_from': datetime(2026, 1, 6, 0, 0, 0),
            'date_to': datetime(2026, 1, 6, 23, 59, 59),
            'calendar_id': self.employee.resource_calendar_id.id,
            'time_type': 'leave',
        })
        self.contract.generate_work_entries(date(2026, 1, 5), date(2026, 1, 7))

        leave = self.env['hr.leave'].create({  # noqa: OLS03001
            'name': 'Worked time leave',
            'employee_id': self.employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2026, 1, 5),
            'request_date_to': date(2026, 1, 7),
        })
        leave.action_approve()

        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '>=', date(2026, 1, 5)),
            ('date', '<=', date(2026, 1, 7)),
            ('active', '=', True),
        ])
        pto_entries = work_entries.filtered(lambda entry: entry.work_entry_type_id == worked_time_type)
        public_holiday_entries = work_entries - pto_entries

        self.assertEqual(len(work_entries), 3)
        self.assertEqual(sorted(pto_entries.mapped('date')), [date(2026, 1, 5), date(2026, 1, 7)])
        self.assertEqual(sorted(pto_entries.mapped('duration')), [8.0, 8.0])
        self.assertEqual(len(public_holiday_entries), 1)
        self.assertEqual(public_holiday_entries.date, date(2026, 1, 6))
        self.assertFalse(public_holiday_entries.work_entry_type_id)

    def test_creating_attendance_regenerate_work_entry(self):
        self.contract.write({
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
        })
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 8, 0, 0),
            'check_out': datetime(2021, 9, 14, 12, 0, 0),
        })

        work_entries1 = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 14, 0, 0),
            'check_out': datetime(2021, 9, 14, 17, 0, 0),
        })

        work_entries2 = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])

        self.assertNotEqual(work_entries1, work_entries2)
        self.assertFalse(work_entries1.active)
        self.assertTrue(work_entries2.active)
        self.assertEqual(work_entries2.duration, 7)

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 18, 0, 0),
            'check_out': datetime(2021, 9, 14, 20, 0, 0),
        })

        work_entries3 = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(work_entries3), 2)

    def test_writing_attendance_regenerate_work_entry(self):
        self.contract.write({
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 8, 0, 0),
            'check_out': datetime(2021, 9, 14, 12, 0, 0),
        })

        work_entries1 = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])

        attendance.write({'check_out': datetime(2021, 9, 14, 17, 0, 0)})

        work_entries2 = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])

        self.assertNotEqual(work_entries1, work_entries2)
        self.assertFalse(work_entries1.active)
        self.assertTrue(work_entries2.active)
        self.assertEqual(work_entries2.duration, 8)

    def test_unlinking_regenerate_work_entry(self):
        self.contract.write({
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
        })
        attendance1 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 8, 0, 0),
            'check_out': datetime(2021, 9, 14, 12, 0, 0),
        })

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 14, 0, 0),
            'check_out': datetime(2021, 9, 14, 17, 0, 0),
        })

        work_entries1 = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])

        attendance1.unlink()
        work_entries2 = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])

        self.assertNotEqual(work_entries1, work_entries2)
        self.assertFalse(work_entries1.active)
        self.assertTrue(work_entries2.active)
        self.assertEqual(work_entries2.duration, 3)

    def test_fully_flexible_employee_overlapping_leaves(self):
        """
        Test Fully Flexible employee with overlapping leaves doesn't cause singleton errors.
        """
        fully_flexible_emp = self.env['hr.employee'].create({
            'name': 'Flexible Employee',
            'date_version': datetime(2025, 6, 1).date(),
            'contract_date_start': datetime(2025, 6, 1).date(),
            'wage': 5000.0,
            'work_entry_source': 'attendance',
            'resource_calendar_id': False,
        })

        sick_leave_type = self.env['hr.work.entry.type'].search([('code', '=', 'LEAVE110')], limit=1)

        self.env['resource.calendar.leaves'].create([
            {
                'name': 'Sick Leave',
                'date_from': datetime(2025, 6, 25),
                'date_to': datetime(2025, 6, 29),
                'resource_id': fully_flexible_emp.resource_id.id,
                'work_entry_type_id': sick_leave_type.id,
            },
            {
                'name': 'Public Holiday',
                'date_from': datetime(2025, 6, 27),
                'date_to': datetime(2025, 6, 27, 23, 59, 59),
                'calendar_id': False,
                'work_entry_type_id': self.work_entry_type_leave.id,
            }
        ])

        # This should NOT raise singleton errors
        fully_flexible_emp.generate_work_entries(
            datetime(2025, 6, 25).date(),
            datetime(2025, 6, 29).date()
        )

    def test_approval_refusal_overtime_regenerates_work_entries_permission(self):
        user = new_test_user(self.env, login="user1", groups="base.group_user")
        self.employee.user_id = user.id

        attendance1 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 13, 8, 0, 0),
            'check_out': datetime(2021, 9, 13, 20, 0, 0),
        })

        with self.assertRaises(AccessError):
            self.assertTrue(attendance1.linked_overtime_ids, "There should be at least one linked overtime line created")
            attendance1.linked_overtime_ids[0].with_user(user).action_approve()
            attendance1.linked_overtime_ids[0].with_user(user).action_refuse()

        self.employee.attendance_manager_id = user.id
        self.assertTrue(user.has_group('hr_attendance.group_hr_attendance_officer'), "User must be attendance officer to approve/refuse overtime")

        attendance2 = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 8, 0, 0),
            'check_out': datetime(2021, 9, 14, 20, 0, 0),
        })

        self.assertTrue(attendance2.linked_overtime_ids, "There should be at least one linked overtime line created")
        # No error should be raised here
        attendance2.linked_overtime_ids[0].with_user(user).action_approve()
        attendance2.linked_overtime_ids[0].with_user(user).action_refuse()

    def test_no_overtime_work_entry_when_no_paid_rules(self):
        """
        If all rules in the ruleset have paid=False,
        OVERTIME work entries must NOT be created.
        """
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Unpaid Ruleset',
            'rule_ids': [Command.create({
                'name': 'Unpaid Rule',
                'base_off': 'quantity',
                'expected_hours_from_contract': True,
                'quantity_period': 'day',
                'paid': False,
            })],
        })
        self.employee.ruleset_id = ruleset
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 1, 10, 8, 0),
            'check_out': datetime(2025, 1, 10, 20, 0),
        })
        self.employee.generate_work_entries(attendance.date, attendance.date)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', attendance.date),
            ('work_entry_type_id.code', '=', 'OVERTIME'),
        ])

        self.assertFalse(
            work_entries,
            "OVERTIME work entries must NOT be created when paid=False"
        )

    def test_overtime_work_entry_created_when_paid_rule_present(self):
        """
        If a ruleset contains a paid rule,
        OVERTIME work entries SHOULD be generated.
        """
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Paid Ruleset',
            'rule_ids': [
                Command.create({
                    'name': 'Paid Rule',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                    'paid': True,
                }),
            ],
        })
        self.employee.ruleset_id = ruleset
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 1, 10, 8, 0),
            'check_out': datetime(2025, 1, 10, 20, 0),
        })
        overtime = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', attendance.date),
        ])
        self.assertTrue(overtime, "Overtime line SHOULD be created with paid rule")
        expected_hours = self.employee.resource_calendar_id.hours_per_day
        expected_overtime = 12 - expected_hours - 1  # lunch hour
        self.assertEqual(overtime.duration, expected_overtime, f"Overtime duration should be {expected_overtime}")

        self.employee.generate_work_entries(attendance.date, attendance.date)
        work_entry = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', attendance.date),
            ('work_entry_type_id.code', '=', 'OVERTIME'),
        ])
        self.assertEqual(len(work_entry), 1)
        self.assertEqual(work_entry.duration, overtime.duration, "OVERTIME work entry duration should match overtime duration")

    def test_multiple_overtime_lines_distribution_multiday_attendance(self):
        """
        Test that multiple overtime lines are correctly distributed when an attendance
        spans multiple days, creating multiple overtime lines that need to be distributed
        across multiple outside-schedule intervals.

        This test should fail when generating work entries if overtime lines overlapped
        """

        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Timing Ruleset',
            'rule_ids': [
                Command.create({
                    'name': 'Outside schedule rule',
                    'base_off': 'timing',
                    'timing_type': 'schedule',
                    'resource_calendar_id': self.env.company.resource_calendar_id.id,
                    'paid': True,
                }),
            ],
        })

        calendar_employee = self.env['hr.employee'].create({
            'name': 'Calendar Employee',
            'tz': 'UTC',
            'work_entry_source': 'calendar',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3500,
            'ruleset_id': ruleset.id,
        })

        attendance = self.env['hr.attendance'].create({
            'employee_id': calendar_employee.id,
            'check_in': datetime(2025, 12, 22, 0, 0),
            'check_out': datetime(2025, 12, 26, 6, 30),
        })

        overtime_lines = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', calendar_employee.id),
            ('date', '>=', date(2025, 12, 22)),
            ('date', '<=', date(2025, 12, 26)),
        ])

        overtime_lines.action_approve()

        attendance.write({
            'check_out': datetime(2025, 12, 27, 6, 30),
        })

        overtime_lines = self.env['hr.attendance.overtime.line'].search([
            ('employee_id', '=', calendar_employee.id),
            ('date', '>=', date(2025, 12, 22)),
            ('date', '<=', date(2025, 12, 27)),
        ])
        overtime_lines.action_approve()

        start_date = date(2025, 12, 22)
        end_date = date(2025, 12, 27)
        calendar_employee.generate_work_entries(start_date, end_date)

    def test_generate_work_entries_with_false_time_stop(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 14, 8, 0, 0),
            'check_out': datetime(2021, 9, 14, 20, 0, 0),
        })
        attendance.linked_overtime_ids[0].time_stop = False

        self.employee.generate_work_entries(date(2021, 9, 14), date(2021, 9, 14))
        work_entry = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(work_entry), 3, 'Three work entries should be generated')

    def test_overtime_crash_multiple_attendances(self):
        """
        Test that creating multiple back-to-back attendances in a timezone that causes work days to span
        midnight (e.g. Adelaide) doesn't cause a 'Expected singleton' crash during work entry generation.
        This scenario occurs when multiple overtime lines apply to the same local day across different
        attendance intervals, particularly when the attendance spans are such that Day 2 contains regular work
        from Attendance 1 and overtime work from Attendance 2.
        """

        self.employee.tz = 'Australia/Adelaide'
        self.employee.resource_calendar_id.tz = 'Australia/Adelaide'

        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Repro Ruleset',
            'rule_ids': [
                (0, 0, {
                    'name': 'Repro Rule',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                    'paid': True,
                })
            ],
        })
        self.employee.ruleset_id = ruleset

        self.contract.write({
            'date_generated_from': date(2026, 2, 1),
            'date_generated_to': date(2026, 3, 31),
        })

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 2, 28, 23, 0, 0),
            'check_out': datetime(2026, 3, 1, 23, 0, 0),
        })

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 3, 1, 23, 0, 0),
            'check_out': datetime(2026, 3, 2, 23, 0, 0),
        })

    def test_overtime_delete_on_attendance_unlink(self):
        """
        Verify that when an attendance is deleted, any associated overtime line records are also
        automatically removed.
        """
        self.employee.tz = 'Australia/Adelaide'
        self.employee.resource_calendar_id.tz = 'Australia/Adelaide'

        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Repro Ruleset',
            'rule_ids': [
                (0, 0, {
                    'name': 'Repro Rule',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                    'paid': True,
                })
            ],
        })
        self.employee.ruleset_id = ruleset

        self.contract.write({
            'date_generated_from': date(2026, 2, 1),
            'date_generated_to': date(2026, 3, 31),
        })

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 2, 28, 23, 0, 0),
            'check_out': datetime(2026, 3, 1, 23, 0, 0),
        })

        overtime_lines = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(overtime_lines)

        attendance.unlink()

        overtime_lines = self.env['hr.attendance.overtime.line'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(overtime_lines)

    def test_regeneration_only_affect_current_day(self):
        """
        Test that when regenerating work entries, if there is an overtime work entry on the day before the selected day to regenerate,
        another one is not added.

        This test should fail if two overtime work entries are present on the previous day after regeneration.
        """

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 3, 10, 8, 0),
            'check_out': datetime(2026, 3, 10, 20, 0),
        })

        self.employee.generate_work_entries(attendance.date, attendance.date)
        work_entry = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', attendance.date),
            ('work_entry_type_id.code', '=', 'OVERTIME'),
        ])

        self.assertEqual(len(work_entry), 1)

        slots = [{"date": date(2026, 3, 10), "employee_id": self.employee.id}, {"date": date(2026, 3, 11), "employee_id": self.employee.id}]
        self.env["hr.work.entry.regeneration.wizard"].regenerate_work_entries(slots=slots)

        work_entry_after_regen = self.env["hr.work.entry"].search(
            [
                ("employee_id", "=", self.employee.id),
                ("date", "=", attendance.date),
                ("work_entry_type_id.code", "=", "OVERTIME"),
            ]
        )

        self.assertEqual(len(work_entry_after_regen), 1, "There should be only one overtime work entry on this day")

    def test_multiple_overlapping_overtimes(self):
        """
        Checks that overtimes are computed correctly even if multiple overtimes are present on the same date, including
        one that overlaps on the day after. This test needs to trigger a specific use case, where we have 2 attendances
        that create overtime, and the second attendance has an overtime for which the end time occurs after the end of
        day UTC. In our case, as we work with Brussels time (GMT+2), our shift ends at
        midnight (so UTC = 22:00:00) but the end of day in GMT+2 is at 23:59:59 (so UTC = 21:59:59).
        """
        self.employee.resource_calendar_id.flexible_hours = False
        self.employee.version_id.resource_calendar_id.tz = self.employee.tz
        self.employee.version_id.write({
            'date_generated_from': date(2026, 2, 1),
            'date_generated_to': date(2026, 10, 31),
        })
        attendance_0, attendance_1 = self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 4, 11, 12, 0, 0),
            'check_out': datetime(2026, 4, 11, 18, 0, 0),
        }, {
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 4, 11, 18, 0, 0),
            'check_out': datetime(2026, 4, 12, 0, 0, 0),
        }])
        self.assertEqual(attendance_0.overtime_hours, 6.0)
        self.assertEqual(attendance_1.overtime_hours, 6.0)

    def test_multiple_overlapping_overtimes_rounding(self):
        """
        Checks that overtimes are computed correctly when an attendance covers multiple dates with separate
        overtimes for each date, a non-UTC timezone, and the overtime durations are rounded.
        """
        self.employee.resource_calendar_id.flexible_hours = False
        self.employee.tz = "Europe/Brussels"
        self.employee.version_id.resource_calendar_id.tz = self.employee.tz
        self.employee.version_id.write({
            'date_generated_from': date(2026, 1, 1),
            'date_generated_to': date(2026, 10, 31),
        })
        attendance_0 = self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 1, 23, 12, 29, 32),
            'check_out': datetime(2026, 1, 24, 0, 29, 44),
        }])
        self.assertAlmostEqual(attendance_0.overtime_hours, 4.003, places=3)

    @freeze_time("2026-04-30 14:00:00")
    def test_automatic_checkout_with_multiple_overtimes(self):
        """
        Checks that a checkout time is correctly generated when the scheduled action of checking out employees is
        executed and such employees have multiple overtime entries for the same day.
        """
        self.employee.resource_calendar_id.flexible_hours = False
        self.employee.company_id.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2
        })
        attendance_1, attendance_2 = self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 4, 18, 6, 0),
            'check_out': datetime(2026, 4, 18, 6, 1)
        }, {
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 4, 18, 6, 2),
            'check_out': False
        }])

        self.env['hr.attendance']._cron_auto_check_out()
        self.assertEqual(attendance_1.overtime_hours + attendance_2.overtime_hours, self.employee.company_id.auto_check_out_tolerance)

    @freeze_time("2026-04-30 14:00:00")
    def test_automatic_checkout_with_timezone(self):
        """
        Checks that a checkout time is correctly generated when the scheduled action of checking out employees is
        executed and such employees have a different timezone than UTC.
        """
        self.employee.write({'tz': 'Europe/Brussels'})
        self.employee.resource_calendar_id.flexible_hours = False
        self.employee.company_id.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 4, 17, 6, 2),
            'check_out': False
        })
        self.env['hr.attendance']._cron_auto_check_out()
        self.assertEqual(attendance.check_out, datetime(2026, 4, 17, 17, 2))

    def test_reset_work_entry_tz_aware_pos(self):
        """
        Test that we can reset the work entries of an employee for a given period and that it correctly regenerates the work entries without impact on other periods, even with timezone involved
        """
        self.employee.tz = 'Europe/Samara'  # utc+4
        self.employee.work_entry_source = 'attendance'
        self.employee.resource_calendar_id.tz = 'Europe/Brussels'  # utc+1
        self.employee.version_id.date_generated_from = date(2026, 4, 1)
        self.employee.version_id.date_generated_to = datetime.max.date()
        self.assertNotEqual(self.employee.tz, self.employee.resource_calendar_id.tz, "The employee and the resource calendar should have different timezones for this test")

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 4, 16, 7, 0, 0),
            'check_out': datetime(2026, 4, 16, 11, 0, 0),
        })

        work_entry = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id), ('date', '=', attendance.date)])
        self.assertEqual(len(work_entry), 1, "One work entry should be generated for the attendance")

        # Regenerate work entries for previous day
        self.env['hr.work.entry.regeneration.wizard'].regenerate_work_entries(
            slots=[{'date': "2026-4-15", 'employee_id': self.employee.id}],
            record_ids=[],
        )

        work_entry = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id), ('date', '=', attendance.date)])
        self.assertEqual(len(work_entry), 1, "Work entry should not be deleted when regenerating for another day")

    def test_reset_work_entry_tz_aware_neg(self):
        """
        Test that we can reset the work entries of an employee for a given period and that it correctly regenerates the work entries without impact on other periods, even with timezone involved
        """
        self.employee.tz = 'America/New_York'  # utc-4
        self.employee.work_entry_source = 'attendance'
        self.employee.resource_calendar_id.tz = 'Europe/Brussels'  # utc+1
        self.employee.version_id.date_generated_from = date(2026, 4, 1)
        self.employee.version_id.date_generated_to = datetime.max.date()
        self.assertNotEqual(self.employee.tz, self.employee.resource_calendar_id.tz, "The employee and the resource calendar should have different timezones for this test")

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 4, 16, 7, 0, 0),
            'check_out': datetime(2026, 4, 16, 11, 0, 0),
        })

        work_entry = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id), ('date', '=', attendance.date)])
        self.assertEqual(len(work_entry), 1, "One work entry should be generated for the attendance")

        # Regenerate work entries for next day
        self.env['hr.work.entry.regeneration.wizard'].regenerate_work_entries(
            slots=[{'date': "2026-4-17", 'employee_id': self.employee.id}],
            record_ids=[],
        )

        work_entry = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id), ('date', '=', attendance.date)])
        self.assertEqual(len(work_entry), 1, "Work entry should not be deleted when regenerating for another day")
