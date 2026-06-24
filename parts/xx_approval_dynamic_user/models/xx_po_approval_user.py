from odoo import api, fields, models


class PoApprovalUser(models.Model):
    _name = "xx.po.approval.user"
    _description = "Purchase Order Dynamic Approver Assignment"
    _order = "notification_order, studio_rule_id"

    order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    studio_rule_id = fields.Many2one(
        comodel_name="studio.approval.rule",
        string="Approval Step",
        required=True,
        ondelete="restrict",
        domain=[("xx_is_dynamic_approver", "=", True)],
    )
    notification_order = fields.Selection(
        related="studio_rule_id.notification_order",
        store=True,
    )
    xx_is_board_approval = fields.Boolean(
        related="studio_rule_id.xx_is_board_approval",
        string="Board Approval",
        store=False,
    )
    # Internal user — set for standard dynamic approval steps.
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned To",
        domain="[('share', '=', False), ('id', 'in', allowed_user_ids)]",
    )
    allowed_user_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_allowed_user_ids",
    )
    allowed_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_allowed_partner_ids",
    )
    # External board member — set for board approval steps.
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Board Member",
    )
    sign_request_id = fields.Many2one(
        comodel_name="sign.request",
        string="Sign Request",
        readonly=True,
    )
    sign_request_state = fields.Selection(
        related="sign_request_id.state",
        string="Signature Status",
        readonly=True,
    )
    sign_access_url = fields.Char(
        compute="_compute_sign_access_url",
        string="Sign Link",
    )

    @api.depends("sign_request_id", "sign_request_id.request_item_ids")
    @api.depends_context("uid")
    def _compute_sign_access_url(self):
        is_admin = self.env.user.has_group("base.group_system")
        for line in self:
            req = line.sign_request_id
            if is_admin and req:
                item = req.request_item_ids[:1]
                line.sign_access_url = (
                    f"/sign/document/{req.id}/{item.access_token}" if item else False
                )
            else:
                line.sign_access_url = False

    _unique_order_rule = models.Constraint(
        "UNIQUE(order_id, studio_rule_id)",
        "Each approval step can only be assigned once per Purchase Order.",
    )

    @api.depends(
        "order_id.company_id",
        "order_id.xx_department_id",
        "studio_rule_id",
        "studio_rule_id.xx_is_board_approval",
    )
    def _compute_allowed_user_ids(self):
        all_internal = self.env["res.users"].search([("share", "=", False)])
        for line in self:
            # Board steps use partner_id instead of user_id.
            if line.studio_rule_id.xx_is_board_approval:
                line.allowed_user_ids = self.env["res.users"]
                continue
            po = line.order_id
            rule = line.studio_rule_id
            if not po.xx_department_id or not rule or not rule.approval_group_id:
                line.allowed_user_ids = all_internal
                continue
            company_id = (po.company_id or self.env.company).id
            matrix_rows = self.env["xx.po.approval.matrix"].search(
                [
                    ("company_id", "=", company_id),
                    ("analytic_account_id", "=", po.xx_department_id.id),
                    ("group_id", "=", rule.approval_group_id.id),
                    ("user_id", "!=", False),
                ]
            )
            if matrix_rows:
                line.allowed_user_ids = matrix_rows.mapped("user_id")
            else:
                # No matrix rows for this dept/group → empty selection forces matrix config first
                line.allowed_user_ids = self.env["res.users"]

    @api.depends(
        "order_id.company_id",
        "order_id.xx_department_id",
        "studio_rule_id",
        "studio_rule_id.xx_is_board_approval",
    )
    def _compute_allowed_partner_ids(self):
        for line in self:
            if not line.studio_rule_id.xx_is_board_approval:
                line.allowed_partner_ids = self.env["res.partner"]
                continue
            po = line.order_id
            rule = line.studio_rule_id
            if not po.xx_department_id or not rule or not rule.approval_group_id:
                line.allowed_partner_ids = self.env["res.partner"]
                continue
            company_id = (po.company_id or self.env.company).id
            matrix_rows = self.env["xx.po.approval.matrix"].search(
                [
                    ("company_id", "=", company_id),
                    ("analytic_account_id", "=", po.xx_department_id.id),
                    ("group_id", "=", rule.approval_group_id.id),
                    ("partner_id", "!=", False),
                ]
            )
            line.allowed_partner_ids = matrix_rows.mapped("partner_id")
