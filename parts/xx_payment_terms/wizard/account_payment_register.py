from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    has_early_discount = fields.Boolean(compute="_compute_has_early_discount", store=False)

    bill_line_ids = fields.One2many(
        "xx.account.payment.register.line", "wizard_id", string="Selected Bill Lines"
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        force_apply_dict = {
            int(k): v for k, v in self.env.context.get("force_apply_writeoff", {}).items()
        }

        if "bill_line_ids" in fields:
            wizard = self.new(res)
            line_vals = []
            for line in wizard.line_ids:
                line_vals.append(
                    (
                        0,
                        0,
                        {
                            "move_id": line.move_id.id,
                            "date_maturity": line.date_maturity,
                            "amount_residual": line.amount_residual,
                            "currency_id": line.currency_id.id,
                            "early_discount": force_apply_dict.get(line.move_id.id, False),
                        },
                    )
                )
            res["bill_line_ids"] = line_vals
        return res

    @api.depends("line_ids")
    def _compute_has_early_discount(self):
        force_apply_dict = {
            int(k): v for k, v in self.env.context.get("force_apply_writeoff", {}).items()
        }

        for wizard in self:
            wizard.has_early_discount = False
            for line in wizard.bill_line_ids:
                if line.discount_expired and not line.early_discount:
                    wizard.has_early_discount = True
                    break
                if (
                    line.early_discount
                    and not force_apply_dict.get(line.move_id.id, False)
                    and line.discount_status != "active"
                    and line.discount_status != ""
                ):
                    wizard.has_early_discount = True
                    break

    def force_apply_writeoff(self):
        force_dict = {}
        for line in self.bill_line_ids:
            force_dict[line.move_id.id] = line.early_discount and line.discount_status == "expired"

        context = dict(self.env.context)
        context["force_apply_writeoff"] = force_dict
        self = self.with_context(force_apply_writeoff=force_dict)

        return {
            "name": self.env._("Pay"),
            "res_model": "account.payment.register",
            "view_mode": "form",
            "views": [[False, "form"]],
            "context": context,
            "target": "new",
            "type": "ir.actions.act_window",
        }

    def action_create_payments(self):
        force_apply_dict = {
            int(k): v for k, v in self.env.context.get("force_apply_writeoff", {}).items()
        }

        unchecked_overrides = self.bill_line_ids.filtered(
            lambda line: line.early_discount
            and not force_apply_dict.get(line.move_id.id, False)
            and line.discount_status != "active"
            and line.discount_status != ""
        )

        if unchecked_overrides:
            raise UserError(
                self.env._(
                    "Some early payment discounts are selected but not yet applied:\n%s",
                    "\n".join(line.move_id.name for line in unchecked_overrides),
                )
            )

        return super().action_create_payments()
