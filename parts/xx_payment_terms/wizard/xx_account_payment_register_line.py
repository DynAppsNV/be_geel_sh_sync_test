from datetime import date, timedelta

from odoo import api, fields, models


class AccountPaymentRegisterLine(models.TransientModel):
    _name = "xx.account.payment.register.line"
    _description = "Bill Lines in Payment Wizard"

    wizard_id = fields.Many2one("account.payment.register", string="Payment Wizard")
    move_id = fields.Many2one("account.move", string="Bill", readonly=True)
    date_maturity = fields.Date(string="Due Date", readonly=True)
    amount_residual = fields.Monetary(string="Residual", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    early_discount = fields.Boolean(string="Apply Early Discount")
    persisted_early_discount = fields.Boolean()

    discount_expired = fields.Boolean(compute="_compute_discount_expired", store=False)
    discount_status = fields.Char(string="Status", compute="_compute_discount_status", store=False)
    discount_date = fields.Date(compute="_compute_discount_date", store=False)

    @api.depends("move_id", "move_id.invoice_date", "move_id.invoice_payment_term_id")
    def _compute_discount_expired(self):
        for line in self:
            line.discount_expired = False
            move = line.move_id
            if move.invoice_payment_term_id:
                if (
                    move.invoice_payment_term_id.early_discount
                    and move.invoice_payment_term_id.discount_percentage
                ):
                    discount_deadline = move.invoice_date + timedelta(
                        days=move.invoice_payment_term_id.discount_days
                    )
                    if date.today() > discount_deadline:
                        line.discount_expired = True

    @api.depends("move_id", "move_id.invoice_date", "move_id.invoice_payment_term_id")
    def _compute_discount_date(self):
        for line in self:
            line.discount_date = False
            move = line.move_id
            if move.invoice_payment_term_id:
                if (
                    move.invoice_payment_term_id.early_discount
                    and move.invoice_payment_term_id.discount_percentage
                ):
                    line.discount_date = move.invoice_date + timedelta(
                        days=move.invoice_payment_term_id.discount_days
                    )

    @api.depends("move_id", "move_id.invoice_date", "move_id.invoice_payment_term_id")
    def _compute_discount_status(self):
        for line in self:
            line.discount_status = ""

            if line.discount_expired and not line.early_discount:
                line.discount_status = "expired"
            elif line.discount_expired and line.early_discount:
                force_apply_dict = {
                    int(k): v for k, v in self.env.context.get("force_apply_writeoff", {}).items()
                }
                if force_apply_dict.get(line.move_id.id, False):
                    line.discount_status = "applied"
                else:
                    line.discount_status = "expired"
            else:
                move = line.move_id
                if move.invoice_payment_term_id:
                    if (
                        move.invoice_payment_term_id.early_discount
                        and move.invoice_payment_term_id.discount_percentage
                    ):
                        discount_deadline = move.invoice_date + timedelta(
                            days=move.invoice_payment_term_id.discount_days
                        )

                        if date.today() <= discount_deadline:
                            line.discount_status = "active"
