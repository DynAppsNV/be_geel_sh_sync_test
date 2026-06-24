from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import datetime


class InheritedPartner(models.Model):
    _inherit = "res.partner"

    xx_credit_line_ids = fields.One2many(
        "xx.credit.line",
        "customer_id",
        "Credit lines",
        domain=lambda self: [
            "|",
            ("expiration_date", "=", False),
            ("expiration_date", ">", datetime.date.today()),
        ],
        readonly=True,
    )
    xx_credit_line_count = fields.Integer(
        string="Credit Lines", compute="_compute_credit_line_count"
    )

    @api.constrains("credit_limit")
    def _check_credit_limit(self):
        for record in self:
            if record.credit_limit < 0:
                raise ValidationError(self.env._("Credit limit cannot be negative."))

    def _compute_credit_line_count(self):
        for partner in self:
            partner.xx_credit_line_count = self.env["xx.credit.line"].search_count(
                [("customer_id", "=", partner.id)]
            )

    def calculate_available_credit(self):
        valid_lines = []

        for record in self:
            credit_lines = self.env["xx.credit.line"].search(
                [("customer_id", "=", record.id), ("date", "<=", datetime.date.today())]
            )

            for line in credit_lines:
                if not line.expiration_date:  # no expiration date
                    valid_lines.append(line)
                elif line.expiration_date > datetime.date.today():  # future expiration date
                    valid_lines.append(line)

            return sum(line.amount for line in valid_lines)

    def calculate_current_credit(self):
        for record in self:
            invoices = self.env["account.move"].search(
                [
                    ("partner_id", "=", record.id),
                    ("payment_state", "in", ["not_paid", "partial", "in_payment"]),
                ]
            )
            amount_residual = sum(invoice.amount_residual for invoice in invoices)
            return amount_residual

    def action_open_credit_lines(self):
        """Open Sale Orders related to this contact"""
        return {
            "name": "Credit Lines",
            "type": "ir.actions.act_window",
            "res_model": "xx.credit.line",
            "view_mode": "list,form",
            "domain": [("customer_id", "=", self.id)],
            "target": "current",
        }
