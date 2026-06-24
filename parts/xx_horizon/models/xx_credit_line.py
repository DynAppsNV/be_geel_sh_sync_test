from odoo import api, fields, models

SYNC_FIELDS = [
    "customer_id",
    "credit_line_type_id",
    "amount",
    "expiration_date",
    "active",
]


class CreditLine(models.Model):
    _inherit = "xx.credit.line"

    active = fields.Boolean(default=True)

    def _after_change_hook(self, method):
        endpoint = (
            self.env["ir.config_parameter"].sudo().get_param("xx_horizon.pas_creditlimit_endpoint")
        )

        for rec in self:
            PartnerModel = self.env["res.partner"].with_company(self.env.company).sudo()
            partner_c = PartnerModel.browse(rec.customer_id.id)
            payment_term = partner_c.property_payment_term_id

            payload = {
                "Code": rec.id,
                "Company_ID": self.env.company.id if payment_term else None,
                "Contact_ID": rec.customer_id.id,
                "Type": rec.credit_line_type_id.code,
                "limit": rec.amount,
                "validationdate": rec.expiration_date.isoformat() if rec.expiration_date else None,
                "Blocked": not rec.active,
            }

            self.env["xx.sync.record"].queue(
                env=self.env,
                model=rec._name,
                payload=payload,
                endpoint=endpoint,
                method=method,
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._after_change_hook("POST")
        return records

    def write(self, vals):
        res = super().write(vals)
        relevant_change = any(field in vals for field in SYNC_FIELDS)

        if relevant_change:
            self._after_change_hook("PUT")

        return res

    def unlink(self):
        self._after_change_hook("DELETE")
        return super().unlink()
