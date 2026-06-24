# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    delete_appraisal = fields.Boolean(string="Delete Future Appraisals", default=True,
        help="Delete all appraisal after contract end date.")

    def action_register_departure(self):
        action = super().action_register_departure()
        appraisal_departures = self.filtered('delete_appraisal')
        leaving_employee_ids = appraisal_departures.employee_ids.ids
        if appraisal_departures:
            future_appraisals = self.env["hr.appraisal"].search([
                ('employee_id', 'in', leaving_employee_ids),
                ('state', 'in', ['1_new', '2_pending'])])
            future_appraisals.sudo().action_back()
            future_appraisals.sudo().unlink()

            future_manager_appraisals = self.env["hr.appraisal"].search([
                ('manager_ids', 'in', leaving_employee_ids),
                ('state', 'in', ['1_new', '2_pending'])])
            for appraisal in future_manager_appraisals:
                appraisal.write({'manager_ids': [(3, emp_id) for emp_id in leaving_employee_ids]})
                appraisal.message_post(body=self.env._(
                    "Appraisal's managers have been updated due to the end of collaboration with an employee."
                ))

            employee_goals = self.env["hr.appraisal.goal"].search([
                ('employee_ids', 'in', leaving_employee_ids)])
            for goal in employee_goals:
                if set(goal.employee_ids.ids) <= set(leaving_employee_ids):
                    goal.sudo().unlink()
        return action
