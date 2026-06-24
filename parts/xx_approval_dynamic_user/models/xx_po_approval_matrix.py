from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PoApprovalMatrix(models.Model):
    _name = "xx.po.approval.matrix"
    _description = "Purchase Order Approval Matrix"
    _order = "analytic_account_id, group_id, sequence"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        required=True,
    )
    group_id = fields.Many2one(
        "res.groups",
        string="Approver Group",
        required=True,
        ondelete="restrict",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Approver",
        domain=[("share", "=", False)],
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Board Member",
        help="External board member who approves via the Sign module.",
    )
    sequence = fields.Integer(default=1)

    @api.constrains("user_id", "partner_id")
    def _check_approver_xor(self):
        for rec in self:
            if not rec.user_id and not rec.partner_id:
                raise ValidationError(
                    self.env._(
                        "Each matrix row must have either an internal approver or a board member."
                    )
                )
            if rec.user_id and rec.partner_id:
                raise ValidationError(
                    self.env._(
                        "A matrix row cannot have both an internal approver and a board member."
                    )
                )

    @api.constrains("company_id", "analytic_account_id", "group_id", "user_id", "partner_id")
    def _check_unique_approver(self):
        for rec in self:
            base_domain = [
                ("id", "!=", rec.id),
                ("company_id", "=", rec.company_id.id),
                ("analytic_account_id", "=", rec.analytic_account_id.id),
                ("group_id", "=", rec.group_id.id),
            ]
            extra = (
                [("user_id", "=", rec.user_id.id)]
                if rec.user_id
                else [("partner_id", "=", rec.partner_id.id)]
            )
            if self.search(base_domain + extra, limit=1):
                raise ValidationError(
                    self.env._(
                        "Each approver can only appear once per department and approver group."
                    )
                )
