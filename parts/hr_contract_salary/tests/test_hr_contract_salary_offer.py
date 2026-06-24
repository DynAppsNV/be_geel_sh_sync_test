# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestHrContractSalaryOffer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })

    def test_preserve_yearly_costs_on_contract_date_change(self):
        self.employee.version_id.final_yearly_costs = 50000
        with Form(self.env['hr.contract.salary.offer'].with_context(default_employee_id=self.employee.id)) as offer_form:
            self.assertEqual(offer_form.contract_template_id, self.employee.version_id)
            self.assertEqual(offer_form.final_yearly_costs, 50000)
            offer_form.final_yearly_costs = 75000
            offer_form.contract_start_date = fields.Date.add(fields.Date.today(), days=15)
        offer = offer_form.save()
        self.assertEqual(offer.final_yearly_costs, 75000)
