from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    xx_approval_line_ids = fields.One2many(
        comodel_name="xx.po.approval.user",
        inverse_name="order_id",
        string="Dynamic Approvers",
        help="Assign a real user to each dynamic approver role required by the approval category.",
    )
    xx_department_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Department",
        tracking=True,
    )

    def _xx_applicable_dynamic_rules(self):
        """Return dynamic approval rules whose domain matches this PO."""
        rules = self.env["studio.approval.rule"].search(
            [
                ("xx_is_dynamic_approver", "=", True),
                ("model_name", "=", "purchase.order"),
            ]
        )
        applicable = self.env["studio.approval.rule"]
        for rule in rules:
            domain = rule.domain and literal_eval(rule.domain)
            if not domain or self.filtered_domain(domain):
                applicable |= rule
        return applicable

    def _xx_get_approval_line_specs(self):
        """Return list of (rule, user_or_False, partner_or_False) for each required approval slot.

        Returns empty list when no department is set. Auto-fills user/partner when the matrix
        has exactly one candidate for the relevant company/department/group combination.
        Board approval rules resolve to a partner; standard rules resolve to a user.
        """
        if not self.xx_department_id:
            return []

        applicable = self._xx_applicable_dynamic_rules()
        specs = []
        company_id = (self.company_id or self.env.company).id

        for rule in applicable:
            if rule.approval_group_id:
                base_domain = [
                    ("company_id", "=", company_id),
                    ("analytic_account_id", "=", self.xx_department_id.id),
                    ("group_id", "=", rule.approval_group_id.id),
                ]
                if rule.xx_is_board_approval:
                    matrix_rows = self.env["xx.po.approval.matrix"].search(
                        base_domain + [("partner_id", "!=", False)]
                    )
                    if matrix_rows:
                        partners = matrix_rows.mapped("partner_id")
                        specs.append((rule, False, partners[0] if len(partners) == 1 else False))
                        continue
                else:
                    matrix_rows = self.env["xx.po.approval.matrix"].search(
                        base_domain + [("user_id", "!=", False)]
                    )
                    if matrix_rows:
                        users = matrix_rows.mapped("user_id")
                        specs.append((rule, users[0] if len(users) == 1 else False, False))
                        continue
            specs.append((rule, False, False))

        return specs

    def _xx_sync_approval_lines(self):
        """Add/update/remove approval lines to match the current matrix configuration."""
        for po in self:
            specs = po._xx_get_approval_line_specs()
            wanted_rule_ids = {r.id for r, _, __ in specs}

            for line in list(po.xx_approval_line_ids):
                if line.studio_rule_id.id not in wanted_rule_ids:
                    line.unlink()

            existing = {ap.studio_rule_id.id: ap for ap in po.xx_approval_line_ids}
            for rule, user, partner in specs:
                if rule.id not in existing:
                    vals = {"order_id": po.id, "studio_rule_id": rule.id}
                    if user:
                        vals["user_id"] = user.id
                    if partner:
                        vals["partner_id"] = partner.id
                    self.env["xx.po.approval.user"].create(vals)
                else:
                    line = existing[rule.id]
                    if user and not line.user_id:
                        line.user_id = user
                    if partner and not line.partner_id:
                        line.partner_id = partner

    @api.constrains("xx_approval_line_ids")
    def _xx_check_approval_lines_complete(self):
        """Raise if any approval line is missing an assigned user or board member."""
        for po in self:
            if not po.xx_department_id:
                continue
            incomplete = po.xx_approval_line_ids.filtered(
                lambda ln: not ln.user_id and not ln.partner_id
            )
            if incomplete:
                steps = ", ".join(
                    ln.studio_rule_id.name or self.env._("Unknown") for ln in incomplete
                )
                raise ValidationError(
                    self.env._(
                        "Please assign an approver for all approval steps before saving: %s",
                        steps,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        pos = super().create(vals_list)
        pos._xx_sync_approval_lines()
        return pos

    def write(self, vals):
        result = super().write(vals)
        if "order_line" in vals or "xx_department_id" in vals:
            self._xx_sync_approval_lines()
        return result

    @api.onchange("order_line", "xx_department_id")
    def _onchange_xx_approvals(self):
        """Real-time sync of approval lines when order lines or department change."""
        specs = self._xx_get_approval_line_specs()
        wanted_rule_ids = {r.id for r, _, __ in specs}

        keep = self.xx_approval_line_ids.filtered(
            lambda ln: ln.studio_rule_id.id in wanted_rule_ids
        )
        # Invalidate cached allowed_* so the domain filter re-evaluates against the new department
        keep.invalidate_recordset(["allowed_user_ids", "allowed_partner_ids"])
        existing_rule_ids = {ln.studio_rule_id.id for ln in keep}

        new_lines = self.env["xx.po.approval.user"]
        for rule, user, partner in specs:
            if rule.id not in existing_rule_ids:
                vals = {"studio_rule_id": rule.id}
                if user:
                    vals["user_id"] = user.id
                if partner:
                    vals["partner_id"] = partner.id
                new_lines |= self.env["xx.po.approval.user"].new(vals)

        self.xx_approval_line_ids = keep | new_lines
