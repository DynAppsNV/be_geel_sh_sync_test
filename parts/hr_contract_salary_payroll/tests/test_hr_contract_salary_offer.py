# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_contract_salary.utils.hr_version import HR_VERSION_CTX_KEY
from odoo.tests import TransactionCase
from datetime import date


class TestHrContractSalaryOffer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.offer_calendar = cls.env['resource.calendar'].create({
            'name': 'Offer Calendar',
            'hours_per_week': 40,
        })
        cls.version_calendar = cls.env['resource.calendar'].create({
            'name': 'Version Calendar',
            'hours_per_day': 7.6,
            'hours_per_week': 38,  # if the version uses this calendar, version.work_time_rate will be 0.95 cause relative to company weekly working hours
            'full_time_required_hours': 38,
        })
        cls.part_time_calendar = cls.env['resource.calendar'].create({
            'name': 'Part Time Calendar',
            'hours_per_week': 20,
        })

        cls.struct_type = cls.env['hr.payroll.structure.type'].create({'name': 'Regular'})
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Regular structure',
            'type_id': cls.struct_type.id,
        })
        cls.struct_type.default_struct_id = cls.structure

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Tom Ato',
            'wage': 2000,
            'structure_type_id': cls.struct_type.id,
            'contract_date_start': date.today()
        })
        cls.version = cls.employee.version_ids[0]
        # Use this context override before calling methods marked with `@requires_hr_version_context`
        # Business code might depend on the context being set correctly, so we don't patch `@requires_hr_version_context`
        cls.version_ctx = {
            'salary_simulation': True,
            'tracking_disable': True,
            HR_VERSION_CTX_KEY: True,
        }

    def test_version_calendar_priority(self):
        offer = self.env['hr.contract.salary.offer'].create({
            'employee_id': self.employee.id,
            'structure_id': self.structure.id,
            'monthly_wage': 2000,
            'resource_calendar_id': self.offer_calendar.id,
        }).with_context(**self.version_ctx)

        # case 1: version calendar empty -> offer calendar is used
        self.version.resource_calendar_id = False
        offer._compute_salary()
        version = offer._get_version()
        self.assertEqual(version.resource_calendar_id, self.offer_calendar)
        self.assertAlmostEqual(offer.gross_wage, 2000.0, places=2)  # check gross salary computed in Salary Simulation Preview

        # case 2: version calendar set -> version calendar is kept
        self.version.resource_calendar_id = self.version_calendar
        offer._compute_salary()
        version = offer._get_version()
        self.assertAlmostEqual(offer.gross_wage, 2000.0, places=2)
        self.assertAlmostEqual(version.work_time_rate, 0.95, 2)

    def test_simulation_calendar_priority(self):
        offer = self.env['hr.contract.salary.offer'].create({
            'employee_id': self.employee.id,
            'structure_id': self.structure.id,
            'monthly_wage': 2000,
            'resource_calendar_id': self.part_time_calendar.id,
            'is_simulation_offer': True,
        })

        # case 1: Check that in case of simulation offer, priority is given to offer calendar over version calendar
        # testing with a part time calendar of 20 hrs/week, we expect gross wage to be half the offer monthly wage
        self.version.resource_calendar_id = self.version_calendar
        offer._compute_salary()
        self.assertAlmostEqual(offer.gross_wage, 1000.0, places=2)  # check gross salary computed in Salary Simulation Preview
