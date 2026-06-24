from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    xx_intrastat_line_ids = fields.One2many(
        comodel_name="xx.intrastat.account.move", inverse_name="move_id", string="Intrastat Lines"
    )

    xx_ignore_intrastat_warning = fields.Boolean()

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        move_type = res.get("move_type")
        if move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
            # Find default transport
            code = self.env["account.intrastat.code"].search(
                [("xx_default_transport", "=", True)], limit=1
            )

            if code:
                res["intrastat_transport_mode_id"] = code.id
            # Find default incoterm
            code = self.env["account.incoterms"].search(
                [("xx_default_incoterm", "=", True)], limit=1
            )
            if code:
                res["invoice_incoterm_id"] = code.id
        return res

    @api.onchange("xx_intrastat_line_ids")
    def _onchange_xx_intrastat_line_ids(self):
        """Fill intrastat_value for newly added lines using the invoice total."""
        total = sum(self.invoice_line_ids.mapped("price_total"))
        for line in self.xx_intrastat_line_ids.filtered(
            lambda rec: not rec.id and not rec.intrastat_value
        ):
            existing_total = sum(
                other.intrastat_value for other in self.xx_intrastat_line_ids if other != line
            )
            remaining = total - existing_total
            line.intrastat_value = max(remaining, 0.0)
            line.intrastat_statistical_value = max(remaining, 0.0)

    def action_post(self):
        for move in self:
            if move.move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
                if move.intrastat_required():
                    if not move.xx_intrastat_line_ids and not move.xx_ignore_intrastat_warning:
                        move.xx_ignore_intrastat_warning = True
                        return {
                            "type": "ir.actions.client",
                            "tag": "display_notification",
                            "params": {
                                "title": "Intrastat Warning",
                                "message": "This invoice has no intrastat lines. "
                                "You can still post if you choose.",
                                "type": "warning",
                                "sticky": False,
                            },
                        }
        return super().action_post()

    def intrastat_required(self):
        company_country = self.company_id.country_id
        partner_country = self.partner_id.country_id

        if not self.company_id.intrastat_region_id:
            return False
        if (
            partner_country == company_country
            or "INTRASTAT" not in partner_country.country_group_codes
        ):
            return False

        return True
