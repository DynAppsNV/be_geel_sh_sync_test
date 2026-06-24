from odoo import models


class SignRequest(models.Model):
    _inherit = "sign.request"

    def write(self, vals):
        result = super().write(vals)
        if vals.get("state") == "signed":
            for request in self:
                request._xx_complete_board_approval()
        return result

    def _xx_complete_board_approval(self):
        """Auto-approve the linked PO board approval step when the sign request is completed."""
        approval_line = (
            self.env["xx.po.approval.user"]
            .sudo()
            .search([("sign_request_id", "=", self.id)], limit=1)
        )
        if not approval_line:
            return
        rule = approval_line.studio_rule_id
        po_id = approval_line.order_id.id
        rule.sudo().with_context(_xx_board_sign_completed=True)._set_approval(po_id, True)
