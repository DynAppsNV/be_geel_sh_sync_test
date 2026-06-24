from odoo.tests import TransactionCase, Form, tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestHrEmployeeBelgiumForm(TransactionCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.be_company = self.env['res.company'].create({
            'name': 'My Belgian Company - TEST',
            'country_id': self.env.ref('base.be').id,
        })
        self.env.user.write({
            'company_ids': [(4, self.be_company.id)],
            'company_id': self.be_company.id,
        })

    def test_belgian_employee_creation_via_form(self):
        with Form(self.env['hr.employee'].with_company(self.be_company)) as employee_form:
            employee_form.name = 'Tony Stark'
            employee_form.contract_date_start = '2025-01-01'
            employee_form.version_id.contract_date_start = '2025-01-01'
            employee_form.wage = 2500.0

        new_employee = employee_form.save()

        self.assertTrue(new_employee.id, "The employee did not save to the database!")
        self.assertEqual(new_employee.name, 'Tony Stark')
        self.assertEqual(str(new_employee.contract_date_start), '2025-01-01')
