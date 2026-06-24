# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase


@tagged('post_install', '-at_install')
class TestPayrollCommission(TestPayslipContractBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # User
        cls.employee_user = cls.env['res.users'].create({
            'login': "Salesman",
            'partner_id': cls.env['res.partner'].create({'name': "Salesman"}).id,
            'group_ids': [Command.set(cls.env.ref('sales_team.group_sale_salesman').ids)],
        })
        # Payslip Input Type
        cls.input = cls.env['hr.payslip.input.type'].create({
            'name': 'Commission',
            'code': 'COMMISSION',
            'country_id': False
        })

    @freeze_time('2024-02-02')
    def test_commission_in_payslip(self):
        today = fields.Date.today()
        employee = self.env['hr.employee'].create({
            'name': 'Salesman',
            'sex': 'male',
            'birthday': '1984-05-01',
            'country_id': self.env.ref('base.be').id,
            'department_id': self.dep_rd.id,
            'user_id': self.employee_user.id,
            'contract_date_end': today + relativedelta(years=2),
            'contract_date_start': today - relativedelta(years=2),
            'wage': 5000.33,
            'structure_type_id': self.structure_type.id,
        })

        # Commission
        product = self.env['product.product'].create({'name': 'Chocolate Cake'})
        commission_plan = self.env['sale.commission.plan'].create({
            'name': "User",
            'company_id': self.env.company.id,
            'date_from': datetime.date(year=2024, month=1, day=1),
            'date_to': datetime.date(year=2024, month=12, day=31),
            'periodicity': 'month',
            'type': 'achieve',
            'user_type': 'person',
            'commission_payroll_input': self.input.id,
        })
        plan_sold, _ = commission_plan.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_sold',
            'rate': 0.04,
            'plan_id': commission_plan.id,
        }, {
            'type': 'amount_invoiced',
            'rate': 0.06,
            'plan_id': commission_plan.id,
        }])
        commission_plan.user_ids = self.env['sale.commission.plan.user'].create([{
            'user_id': self.employee_user.id,
            'plan_id': commission_plan.id,
        }])
        commission_plan.action_approve()

        # Sale order
        partner = self.env["res.partner"].create({"name": 'Buyer', "company_id": self.env.company.id})
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'user_id': self.employee_user.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
        })
        so.action_confirm()
        self.env.invalidate_all()
        self.env['sale.commission.achievement.report']._pre_achievement_operation()
        achievements = self.env['sale.commission.achievement.report'].sudo().search([('plan_id', '=', commission_plan.id)])
        self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
        commission_amount = so.amount_untaxed * plan_sold.rate
        self.assertEqual(achievements.achieved, commission_amount)

        payslip = self.env['hr.payslip'].create({'name': 'Payslip', 'employee_id': employee.id})
        self.assertEqual(payslip.input_line_ids.filtered(lambda l: l.input_type_id.id == self.input.id).amount, commission_amount)

    @freeze_time('2026-01-15')
    def test_multiple_commission_in_payslip(self):
        """ Ensure commissions from multiple plans are aggregated into a single payslip input. """
        base_company = self.env.ref("base.main_company")
        today = fields.Date.today()
        employee = self.env["hr.employee"].create({
                "name": "Salesman",
                "sex": "male",
                "birthday": "1984-05-01",
                "country_id": self.env.ref("base.be").id,
                "department_id": self.dep_rd.id,
                "user_id": self.employee_user.id,
                "contract_date_end": today + relativedelta(years=2),
                "contract_date_start": today - relativedelta(years=2),
                "wage": 5000.33,
                "structure_type_id": self.structure_type.id,
            })

        common_plan_vals = {
            "date_from": datetime.date(2026, 1, 1),
            "date_to": datetime.date(2026, 12, 31),
            "periodicity": "month",
            "type": "achieve",
            "user_type": "person",
            "commission_payroll_input": self.input.id,
            "user_ids": [Command.create({"user_id": self.employee_user.id})],
        }
        # Commission Plans - have a default 5% 'amount_invoiced' achievement
        plans = self.env['sale.commission.plan'].create([
            dict(common_plan_vals, name="5% on Sales"),
            dict(
                common_plan_vals, name="10% on Sales",
                achievement_ids=[Command.create({'type': 'amount_invoiced', 'rate': 0.10})]
            ),
        ])
        plans.action_approve()

        # Create and invoice a sale order assigned to the commission user
        so = self.env['sale.order'].with_company(base_company).create({
            'partner_id': self.env['res.partner'].create({'name': 'Buyer'}).id,
            'user_id': self.employee_user.id,
            'order_line': [Command.create({
                'product_id': self.env['product.product'].create({'name': 'Cookies'}).id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
        })
        so.action_confirm()
        invoice = self.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order',
            active_id=so.id,
        ).create({'advance_payment_method': 'delivered'})._create_invoices(so)
        invoice.action_post()

        self.env.invalidate_all()
        achievements = self.env['sale.commission.achievement.report'].with_company(base_company).search([
            ('user_id', '=', self.employee_user.id)
        ])
        self.assertEqual(len(achievements), 2)

        # expected total commission from all plans
        total_commission = sum(
            so.amount_untaxed * plan.achievement_ids[0].rate for plan in plans
        )
        self.assertEqual(sum(achievements.mapped('achieved')), total_commission)

        # Ensure payslip aggregates all commissions into the same input line
        payslip = self.env['hr.payslip'].with_company(base_company).create({
            'name': 'Payslip',
            'employee_id': employee.id,
        })
        self.assertEqual(
            total_commission,
            payslip.input_line_ids.filtered(lambda l: l.input_type_id == self.input).amount,
        )
