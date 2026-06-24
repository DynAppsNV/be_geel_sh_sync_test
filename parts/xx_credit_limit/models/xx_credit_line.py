from datetime import timedelta

from odoo import fields, models


class CreditLine(models.Model):
    _name = "xx.credit.line"
    _description = "Credit Line"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    customer_id = fields.Many2one(string="Customer", comodel_name="res.partner", required=True)
    credit_line_type_id = fields.Many2one(
        string="Type", comodel_name="xx.credit.line.type", required=True, tracking=True
    )
    date = fields.Date(required=True, tracking=True)
    name_insurance_company_id = fields.Many2one(comodel_name="res.bank")
    contract_number = fields.Integer(tracking=True)
    our_reference = fields.Char()
    insurance_company_reference = fields.Char()
    expiration_date = fields.Date(tracking=True)
    amount = fields.Float()
    currency_id = fields.Many2one(string="Currency", comodel_name="res.currency", required=True)
    comments = fields.Text()
    change_reason = fields.Text()
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        domain=[("res_model", "=", "xx.credit.line")],
        string="Attachments",
    )

    def server_action_increment_expiration(self):
        for record in self:
            if record.expiration_date:
                record.expiration_date = record.expiration_date + timedelta(days=365)

        return True
