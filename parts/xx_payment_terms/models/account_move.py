from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_toggle_early_payment_discount(self):
        for move in self:
            move.early_payment_discount = not move.early_payment_discount

    @api.depends(
        "currency_id",
        "move_type",
        "invoice_payment_term_id",
        "invoice_payment_term_id.early_discount",
        "invoice_date",
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
    )
    def _compute_early_payment_discount(self):
        for move in self:
            if move.early_payment_discount is None:
                move.early_payment_discount = move._is_eligible_for_early_payment_discount(
                    move.currency_id,
                    move.invoice_date,
                )

    def _inverse_early_payment_discount(self):
        # No logic needed — this allows manual write
        pass

    def _is_eligible_for_early_payment_discount(self, currency, reference_date):
        self.ensure_one()

        force_apply_dict = {
            int(k): v for k, v in self.env.context.get("force_apply_writeoff", {}).items()
        }

        if force_apply_dict.get(self.id):
            return True

        payment_terms = self.line_ids.filtered(lambda line: line.display_type == "payment_term")
        return (
            self.currency_id == currency
            and self.move_type in self._early_payment_discount_move_types()
            and self.invoice_payment_term_id.early_discount
            and (
                not reference_date
                or not self.invoice_date
                or (
                    (existing_discount_date := next(iter(payment_terms)).discount_date)
                    and reference_date <= existing_discount_date
                )
            )
            and not (
                payment_terms.sudo().matched_debit_ids + payment_terms.sudo().matched_credit_ids
            )
        )
