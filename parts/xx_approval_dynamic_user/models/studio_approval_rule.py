import base64
import io
from ast import literal_eval

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.pdf import PdfFileReader


class StudioApprovalRule(models.Model):
    _inherit = "studio.approval.rule"

    xx_is_dynamic_approver = fields.Boolean(
        string="Dynamic Approver",
        default=False,
        help=(
            "When checked, this approver slot is a placeholder. "
            "The actual approver is resolved from the Purchase Order's Approvers tab. "
            "The Approval Group field is used as the matrix key to look up available approvers."
        ),
    )
    xx_is_board_approval = fields.Boolean(
        string="Board Approval",
        default=False,
        help=(
            "When checked, approval is collected from an external board member via the Sign "
            "module instead of an internal Odoo user."
        ),
    )

    @api.depends_context("uid", "_xx_board_sign_completed")
    def _compute_can_validate(self):
        res = super()._compute_can_validate()
        user = self.env.user
        for rule in self.filtered("xx_is_dynamic_approver"):
            if rule.can_validate:
                continue
            # Board approval is completed via Sign — grant can_validate only for the
            # programmatic completion path; block direct Odoo button access otherwise.
            if rule.xx_is_board_approval:
                if self.env.context.get("_xx_board_sign_completed"):
                    rule.can_validate = True
                continue
            assigned = self.env["xx.po.approval.user"].search(
                [("studio_rule_id", "=", rule.id), ("user_id", "=", user.id)],
                limit=1,
            )
            if assigned:
                rule.can_validate = True
        return res

    def check_approval(self, model_name, res_id, method_name, action_id):
        """Snapshot pre-call approved state so within-call auto-approvals don't satisfy
        the sequential guard for later steps in the same check_approval pass."""
        if model_name == "purchase.order":
            pre_approved_ids = frozenset(
                self.env["studio.approval.entry"]
                .sudo()
                .search(
                    [
                        ("model", "=", "purchase.order"),
                        ("res_id", "=", res_id),
                        ("approved", "=", True),
                    ]
                )
                .mapped("rule_id")
                .ids
            )
            self = self.with_context(_xx_pre_approved_rule_ids=pre_approved_ids)
        return super().check_approval(model_name, res_id, method_name, action_id)

    def _xx_prior_steps_approved(self, res_id):
        """Return True if all dynamic PO rules with a lower notification_order are approved.

        Uses the pre-call snapshot stored in context when available, so that a step
        auto-approved earlier in the same check_approval pass cannot unlock the next step.
        """
        ruleSudo = self.sudo()
        po = self.env["purchase.order"].browse(res_id)
        candidates = (
            self.env["studio.approval.rule"]
            .sudo()
            .search(
                [
                    ("xx_is_dynamic_approver", "=", True),
                    ("model_name", "=", "purchase.order"),
                    ("notification_order", "<", ruleSudo.notification_order),
                ]
            )
        )
        prior_rules = self.env["studio.approval.rule"]
        for rule in candidates:
            domain = rule.domain and literal_eval(rule.domain)
            if not domain or po.filtered_domain(domain):
                prior_rules |= rule

        if not prior_rules:
            return True

        # Prefer the pre-call snapshot so within-call auto-approvals don't chain.
        pre_approved_ids = self.env.context.get("_xx_pre_approved_rule_ids")
        if pre_approved_ids is not None:
            approved_ids = pre_approved_ids
        else:
            approved_ids = set(
                self.env["studio.approval.entry"]
                .sudo()
                .search(
                    [
                        ("model", "=", "purchase.order"),
                        ("res_id", "=", res_id),
                        ("rule_id", "in", prior_rules.ids),
                        ("approved", "=", True),
                    ]
                )
                .mapped("rule_id")
                .ids
            )
        return all(r.id in approved_ids for r in prior_rules)

    def _create_request(self, res_id):
        """Route board approval rules to Sign; internal rules get a mail activity."""
        if not self.sudo().xx_is_dynamic_approver or self.sudo().model_name != "purchase.order":
            return super()._create_request(res_id)

        if not self._xx_prior_steps_approved(res_id):
            return False

        if self.sudo().xx_is_board_approval:
            return self._create_board_sign_request(res_id)

        ruleSudo = self.sudo()
        if not ruleSudo.model_id.is_mail_activity:
            return False

        if (
            self.env["studio.approval.request"]
            .sudo()
            .search([("rule_id", "=", self.id), ("res_id", "=", res_id)], limit=1)
        ):
            return False

        po = self.env["purchase.order"].browse(res_id)
        assigned_lines = po.xx_approval_line_ids.filtered(
            lambda ln: ln.studio_rule_id == self and ln.user_id
        )
        if not assigned_lines:
            return False

        record = self.env[ruleSudo.model_name].browse(res_id)
        for po_line in assigned_lines:
            activity = record.activity_schedule(
                activity_type_id=self.env.ref("mail.mail_activity_data_todo").id,
                user_id=po_line.user_id.id,
                summary=self.env._("Grant Approval"),
            )
            self.env["studio.approval.request"].sudo().create(
                {"rule_id": self.id, "mail_activity_id": activity.id, "res_id": res_id}
            )
        return True

    def _create_board_sign_request(self, res_id):
        """Render the PO PDF, place a signature field on the last page, send to board member."""
        if (
            self.env["studio.approval.request"]
            .sudo()
            .search([("rule_id", "=", self.id), ("res_id", "=", res_id)], limit=1)
        ):
            return False

        po = self.env["purchase.order"].browse(res_id)
        po_line = po.xx_approval_line_ids.filtered(
            lambda ln: ln.studio_rule_id == self and ln.partner_id
        )[:1]
        if not po_line:
            raise UserError(
                self.env._(
                    "No board member has been assigned for the '%(step)s' approval step"
                    " on %(po)s. Please fill in the Board Member field on the Approvers"
                    " tab before requesting approval.",
                    step=self.sudo().name or self.env._("Board Approval"),
                    po=po.name,
                )
            )

        partner = po_line.partner_id
        role = self.env.ref("xx_approval_dynamic_user.sign_item_role_board_member")

        pdf_content, _ = self.env["ir.actions.report"]._render_qweb_pdf(
            "purchase.action_report_purchase_order", [po.id]
        )
        last_page = len(PdfFileReader(io.BytesIO(pdf_content)).pages)

        get_param = self.env["ir.config_parameter"].sudo().get_param
        pos_x = float(get_param("xx_approval_dynamic_user.board_sign_pos_x", 0.70))
        pos_y = float(get_param("xx_approval_dynamic_user.board_sign_pos_y", 0.90))
        width = float(get_param("xx_approval_dynamic_user.board_sign_width", 0.20))
        height = float(get_param("xx_approval_dynamic_user.board_sign_height", 0.05))

        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": self.env._("%s — Board Approval.pdf", po.name),
                    "datas": base64.b64encode(pdf_content).decode(),
                    "mimetype": "application/pdf",
                }
            )
        )

        template = (
            self.env["sign.template"]
            .sudo()
            .create(
                {
                    "name": self.env._("Board Approval — %s", po.name),
                    "document_ids": [
                        Command.create(
                            {
                                "attachment_id": attachment.id,
                                "sign_item_ids": [
                                    Command.create(
                                        {
                                            "type_id": self.env.ref(
                                                "sign.sign_item_type_signature"
                                            ).id,
                                            "responsible_id": role.id,
                                            "page": last_page,
                                            "posX": pos_x,
                                            "posY": pos_y,
                                            "width": width,
                                            "height": height,
                                        }
                                    )
                                ],
                            }
                        )
                    ],
                }
            )
        )

        lang = partner.lang or self.env.lang or "en_US"
        env_lang = self.with_context(lang=lang).env
        step_name = self.sudo().with_context(lang=lang).name or env_lang._("Board Approval")
        reference = env_lang._("Board Approval — %s", po.name)
        sign_request = (
            self.env["sign.request"]
            .sudo()
            .create(
                {
                    "template_id": template.id,
                    "reference": reference,
                    "subject": env_lang._("%(step)s — %(po)s", step=step_name, po=po.name),
                    "request_item_ids": [
                        Command.create({"partner_id": partner.id, "role_id": role.id})
                    ],
                }
            )
        )
        po_line.sudo().sign_request_id = sign_request
        return True

    def _set_approval(self, res_id, approved):
        """Enforce per-PO approver assignment; bypass user check for board sign completion."""
        if not self.sudo().xx_is_dynamic_approver or self.sudo().model_name != "purchase.order":
            return super()._set_approval(res_id, approved)

        po = self.env["purchase.order"].browse(res_id)
        po_lines = po.sudo().xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self)
        if not po_lines:
            raise UserError(
                self.env._(
                    "No approver has been assigned for this approval step on the Purchase Order."
                )
            )

        # Board approval is triggered programmatically after sign completion.
        if po_lines[:1].partner_id and self.env.context.get("_xx_board_sign_completed"):
            return super()._set_approval(res_id, approved)

        if not self._xx_prior_steps_approved(res_id):
            raise UserError(self.env._("A prior approval step has not been completed yet."))

        if not po_lines.filtered(lambda ln: ln.user_id == self.env.user):
            raise UserError(self.env._("You are not the assigned approver for this approval step."))

        return super()._set_approval(res_id, approved)
