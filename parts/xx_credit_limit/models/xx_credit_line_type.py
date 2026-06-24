from odoo import api, fields, models


class CreditLineType(models.Model):
    _name = "xx.credit.line.type"
    _description = "Credit Line Type"
    _rec_name = "code"

    code = fields.Char()
    description = fields.Char(required=True, translate=True)
    own_risk = fields.Boolean()

    @api.depends("description")
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.description
