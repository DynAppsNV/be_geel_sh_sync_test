# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import tagged
from .common import TestPayrollCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEmployeeFirstContractDate(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.version_1 = cls.employee_georges.create_version({
            'date_version': '2020-12-01',
            'contract_date_start': '2020-12-01',
            'contract_date_end': '2020-12-31',
            'active': True
        })

        cls.version_2 = cls.employee_georges.create_version({
            'date_version': '2020-11-01',
            'contract_date_start': '2020-11-01',
            'contract_date_end': '2020-11-30',
            'active': True
        })

        cls.version_3 = cls.employee_georges.create_version({
            'date_version': '2020-10-01',
            'contract_date_start': '2020-10-01',
            'contract_date_end': '2020-10-31',
            'active': False
        })

    def test_first_contract_date_on_create(self):
        employee = self.env['hr.employee'].create({
            'name': 'Jane Doe',
            'date_version': '2020-12-01',
            'contract_date_start': '2020-12-01',
            'contract_date_end': '2020-12-31'
        })

        self.assertEqual(
            employee.first_contract_in_company,
            date(2020, 12, 1),
            "First contract date should be 2020-12-01 when creating an employee with a single contract."
        )

    def test_multiple_contract_first_date_on_create(self):
        self.employee_georges._invalidate_cache(['first_contract_in_company'])
        self.assertEqual(
            self.employee_georges.first_contract_in_company,
            date(2020, 11, 1),
            "First contract date should be 2020-11-01 when creating an employee with multiple contracts."
        )

    def test_first_contract_date_on_write(self):
        self.version_2.write({'contract_date_start': '2020-05-02'})
        self.employee_georges._invalidate_cache(['first_contract_in_company'])
        self.assertEqual(
            self.employee_georges.first_contract_in_company,
            date(2020, 5, 2),
            "Expected first contract date to update to 2020-05-02 after modifying the earliest contract."
        )

    def test_first_contract_date_on_delete(self):
        self.version_2.unlink()
        self.employee_georges._invalidate_cache(['first_contract_in_company'])
        self.assertEqual(
            self.employee_georges.first_contract_in_company,
            date(2020, 12, 1),
            "Expected first contract date to update to 2020-12-01 after deletion of the earliest contract."
        )

    def test_first_contract_date_on_archive_and_unarchive(self):
        self.employee_georges._invalidate_cache(['first_contract_in_company'])
        self.assertEqual(
            self.employee_georges.first_contract_in_company,
            date(2020, 11, 1),
            "First contract date should be the earliest active contract before archiving."
        )

        # Archive earliest version
        self.version_2.active = False
        self.employee_georges._invalidate_cache(['first_contract_in_company'])
        self.assertEqual(
            self.employee_georges.first_contract_in_company,
            date(2020, 12, 1),
            "First contract date should be the next earliest active contract before archiving."
        )

        # Unarchive earliest version
        self.version_2.active = True
        self.employee_georges._invalidate_cache(['first_contract_in_company'])
        self.assertEqual(
            self.employee_georges.first_contract_in_company,
            date(2020, 11, 1),
            "First contract date should revert when the earliest contract is unarchived."
        )
