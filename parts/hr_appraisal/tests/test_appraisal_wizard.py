from odoo.tests.common import TransactionCase, tagged
from odoo.tests import new_test_user


@tagged('post_install', '-at_install')
class TestAppraisalWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.template = cls.env['hr.appraisal.template'].create({
            'description': 'Test appraisal template'
        })

        cls.admin_user = new_test_user(cls.env, login='admin_user', name='Admin User', groups='hr_appraisal.group_hr_appraisal_manager')

        cls.manager_user = new_test_user(cls.env, login='Usseif', name='Youssef Ahmed')
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Youssef Ahmed',
            'user_id': cls.manager_user.id,
        })
        cls.employee_micheal = cls.env['hr.employee'].create({
            'name': "Michael Hawkin",
            'parent_id': cls.manager.id,
        })
        cls.employee_john = cls.env['hr.employee'].create({
            'name': 'John Doe',
        })

    def test_01_get_employees_from_mode_as_admin_user(self):
        """ Verify that an User Admin access all employees regardless of hierarchy """
        wizard = self.env['hr.appraisal.campaign.wizard'].with_user(self.admin_user).create({
            'mode': 'employee',
            'appraisal_template_id': self.template.id,
        })

        employees = wizard._get_employees_from_mode()

        self.assertIn(self.manager, employees, "Admin should see the manager")
        self.assertIn(self.employee_micheal, employees, "Admin should see the subordinate")
        self.assertIn(self.employee_john, employees, "Admin should see the outsider")

    def test_02_get_employees_from_mode_as_manager(self):
        """ Verify that the wizard only fetches subordinates for a regular manager """
        wizard = self.env['hr.appraisal.campaign.wizard'].with_user(self.manager_user).create({
            'mode': 'employee',
            'appraisal_template_id': self.template.id,
        })

        employees = wizard._get_employees_from_mode()

        self.assertIn(self.manager, employees, "Manager should see himself")
        self.assertIn(self.employee_micheal, employees, "Manager should see their subordinate")
        self.assertNotIn(self.employee_john, employees, "Manager shouldn't see employees outside their hierarchy")

    def test_03_get_employees_from_mode_with_specific_selection(self):
        """ Verify that if employee_ids are manually selected, they are returned directly """
        wizard = self.env['hr.appraisal.campaign.wizard'].with_user(self.manager_user).create({
            'mode': 'employee',
            'appraisal_template_id': self.template.id,
            'employee_ids': [(6, 0, [self.employee_micheal.id])]
        })

        employees = wizard._get_employees_from_mode()

        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0], self.employee_micheal)
