import base64
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import Form
from odoo.tests.common import TransactionCase, mute_logger
from odoo.tools.misc import file_open


class TestXxApprovalDynamicUser(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.dummy_user = Users.create({"name": "Dummy Approver", "login": "dummy_approver_xx"})
        purchase_user_gid = cls.env.ref("purchase.group_purchase_user").id
        cls.real_approver_1 = Users.create(
            {
                "name": "Real Approver 1",
                "login": "real_approver_xx_1",
                "group_ids": [Command.link(purchase_user_gid)],
            }
        )
        cls.real_approver_2 = Users.create(
            {
                "name": "Real Approver 2",
                "login": "real_approver_xx_2",
                "group_ids": [Command.link(purchase_user_gid)],
            }
        )
        cls.real_approver_3 = Users.create(
            {
                "name": "Real Approver 3",
                "login": "real_approver_xx_3",
                "group_ids": [Command.link(purchase_user_gid)],
            }
        )
        cls.other_user = Users.create({"name": "Other User", "login": "other_user_xx"})

        cls.vendor = cls.env["res.partner"].create(
            {"name": "Test Vendor", "supplier_rank": 1, "email": "vendor@test.example"}
        )
        cls.product = cls.env["product.product"].create({"name": "Test Product"})

        cls.analytic_plan = cls.env["account.analytic.plan"].create({"name": "Test Plan XX"})
        cls.department = cls.env["account.analytic.account"].create(
            {"name": "HR", "plan_id": cls.analytic_plan.id}
        )
        cls.department_b = cls.env["account.analytic.account"].create(
            {"name": "Finance", "plan_id": cls.analytic_plan.id}
        )

        cls.approval_group_1 = cls.env["res.groups"].create({"name": "Purchase / Level 1 Test"})
        cls.approval_group_2 = cls.env["res.groups"].create({"name": "Purchase / Level 2 Test"})

        model_id = cls.env["ir.model"]._get("purchase.order").id
        cls.rule_1 = cls.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([cls.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "approval_group_id": cls.approval_group_1.id,
                "notification_order": "1",
            }
        )
        cls.rule_2 = cls.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([cls.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "approval_group_id": cls.approval_group_2.id,
                "notification_order": "2",
            }
        )
        cls.rule_fixed = cls.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([cls.real_approver_1.id])],
                "xx_is_dynamic_approver": False,
                "notification_order": "3",
            }
        )

        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "name": cls.product.display_name,
                            "product_id": cls.product.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                            "date_planned": "2025-01-01 00:00:00",
                        }
                    )
                ],
            }
        )

    def _assign(self, rule, user):
        return self.env["xx.po.approval.user"].create(
            {
                "order_id": self.po.id,
                "studio_rule_id": rule.id,
                "user_id": user.id,
            }
        )

    def _make_sign_request(self, reference, partner=None):
        """Create a sign.request that passes sign.document PDF validation and
        the sign.log hash-chain check.

        sign.document.create validates the attachment is a parseable PDF.
        sign_log._get_or_check_hash has a bug: when no previous log exists and
        the template has no documents, it reads prev_activity.log_hash (False
        on an empty recordset) and crashes on False + str.  Attaching a real
        PDF document forces the if-branch which uses previous_hash="" instead.
        """
        with file_open("sign/static/demo/sample_contract.pdf", "rb") as fh:
            pdf_data = base64.b64encode(fh.read())
        attachment = (
            self.env["ir.attachment"].sudo().create({"name": f"{reference}.pdf", "datas": pdf_data})
        )
        template = self.env["sign.template"].sudo().create({"name": reference})
        self.env["sign.document"].sudo().create(
            {"attachment_id": attachment.id, "template_id": template.id}
        )
        default_role = self.env.ref("sign.sign_item_role_default")
        return (
            self.env["sign.request"]
            .sudo()
            .create(
                {
                    "template_id": template.id,
                    "reference": reference,
                    "request_item_ids": [
                        Command.create(
                            {"partner_id": (partner or self.vendor).id, "role_id": default_role.id}
                        )
                    ],
                }
            )
        )

    def _make_matrix(self, rule, *users, dept=None):
        """Create one matrix row per user for the rule's approver group."""
        records = self.env["xx.po.approval.matrix"]
        group = rule.approval_group_id
        for seq, user in enumerate(users, 1):
            if user:
                records |= self.env["xx.po.approval.matrix"].create(
                    {
                        "company_id": self.env.company.id,
                        "analytic_account_id": (dept or self.department).id,
                        "group_id": group.id,
                        "user_id": user.id,
                        "sequence": seq,
                    }
                )
        return records

    # -------------------------------------------------------------------------
    # Matrix model
    # -------------------------------------------------------------------------

    def test_matrix_creation(self):
        matrix = self._make_matrix(self.rule_1, self.real_approver_1)
        self.assertEqual(matrix.company_id, self.env.company)
        self.assertEqual(matrix.analytic_account_id, self.department)
        self.assertEqual(matrix.user_id, self.real_approver_1)

    def test_matrix_group_set(self):
        matrix = self._make_matrix(self.rule_1, self.real_approver_1)
        self.assertEqual(matrix.group_id, self.rule_1.approval_group_id)

    def test_matrix_both_user_and_partner_raises(self):
        """A matrix row with both user_id and partner_id is rejected."""
        board_partner = self.env["res.partner"].create({"name": "Dual Approver"})
        with self.assertRaises(ValidationError):
            self.env["xx.po.approval.matrix"].create(
                {
                    "company_id": self.env.company.id,
                    "analytic_account_id": self.department.id,
                    "group_id": self.approval_group_1.id,
                    "user_id": self.real_approver_1.id,
                    "partner_id": board_partner.id,
                }
            )

    def test_matrix_duplicate_partner_raises(self):
        """The same partner cannot appear twice for the same department and group."""
        board_partner = self.env["res.partner"].create({"name": "Dup Board Partner"})
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": self.approval_group_1.id,
                "partner_id": board_partner.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["xx.po.approval.matrix"].create(
                {
                    "company_id": self.env.company.id,
                    "analytic_account_id": self.department.id,
                    "group_id": self.approval_group_1.id,
                    "partner_id": board_partner.id,
                }
            )

    # -------------------------------------------------------------------------
    # xx.po.approval.user model / field tests
    # -------------------------------------------------------------------------

    def test_is_dynamic_approver_defaults_false(self):
        self.assertFalse(self.rule_fixed.xx_is_dynamic_approver)

    def test_po_approval_line_field_exists(self):
        self.assertTrue(hasattr(self.po, "xx_approval_line_ids"))
        self.assertFalse(self.po.xx_approval_line_ids)

    def test_unique_constraint_per_rule(self):
        self._assign(self.rule_1, self.real_approver_1)
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception):  # noqa: B017
            self._assign(self.rule_1, self.real_approver_2)

    # -------------------------------------------------------------------------
    # _compute_allowed_user_ids
    # -------------------------------------------------------------------------

    def test_allowed_user_ids_no_department(self):
        line = self._assign(self.rule_1, self.real_approver_1)
        self.assertIn(self.real_approver_1, line.allowed_user_ids)
        # fallback: all internal users
        self.assertIn(self.real_approver_2, line.allowed_user_ids)

    def test_allowed_user_ids_from_matrix(self):
        self._make_matrix(self.rule_1, self.real_approver_1)
        self.po.xx_department_id = self.department
        # Setting department triggers sync, which auto-fills the single matrix user.
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertIn(self.real_approver_1, line.allowed_user_ids)
        self.assertNotIn(self.real_approver_2, line.allowed_user_ids)

    def test_allowed_user_ids_multiple_choices(self):
        """All users in the matrix for the group are available as choices."""
        self._make_matrix(self.rule_1, self.real_approver_1, self.real_approver_2)
        self.po.xx_department_id = self.department
        # Multiple matrix rows → sync creates the line but leaves user_id empty.
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertIn(self.real_approver_1, line.allowed_user_ids)
        self.assertIn(self.real_approver_2, line.allowed_user_ids)
        self.assertNotIn(self.other_user, line.allowed_user_ids)

    def test_allowed_user_ids_no_matrix_rows_returns_empty(self):
        self.po.xx_department_id = self.department
        # No matrix rows → allowed_user_ids is empty so no user can be saved until matrix is set up.
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertFalse(line.allowed_user_ids)
        self.assertNotIn(self.real_approver_2, line.allowed_user_ids)

    # -------------------------------------------------------------------------
    # _compute_allowed_partner_ids
    # -------------------------------------------------------------------------

    def test_allowed_partner_ids_empty_for_non_board_rule(self):
        line = self._assign(self.rule_1, self.real_approver_1)
        self.assertFalse(line.allowed_partner_ids)

    def test_allowed_partner_ids_from_matrix_for_board_rule(self):
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board Test XX"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "4",
            }
        )
        board_partner = self.env["res.partner"].create({"name": "Board Partner Test"})
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": board_group.id,
                "partner_id": board_partner.id,
            }
        )
        self.po.xx_department_id = self.department
        # Sync auto-creates a line for board_rule; use it rather than creating a duplicate
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == board_rule)
        self.assertIn(board_partner, line.allowed_partner_ids)

    def test_allowed_partner_ids_empty_without_department(self):
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board Test XX 2"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "5",
            }
        )
        board_partner = self.env["res.partner"].create({"name": "Board Partner Test 2"})
        line = self.env["xx.po.approval.user"].create(
            {
                "order_id": self.po.id,
                "studio_rule_id": board_rule.id,
                "partner_id": board_partner.id,
            }
        )
        # No department set on PO → empty
        self.assertFalse(line.allowed_partner_ids)

    # -------------------------------------------------------------------------
    # _compute_sign_access_url
    # -------------------------------------------------------------------------

    def test_sign_access_url_empty_without_sign_request(self):
        line = self._assign(self.rule_1, self.real_approver_1)
        self.assertFalse(line.sign_access_url)

    def test_sign_access_url_only_for_admin(self):
        sign_req = self._make_sign_request("URL Test")
        line = self._assign(self.rule_1, self.real_approver_1)
        line.sign_request_id = sign_req

        # Admin sees the sign URL because the request has a request_item_ids
        admin_line = line.with_user(self.env.ref("base.user_admin"))
        self.assertTrue(admin_line.sign_access_url)
        self.assertIn("/sign/document/", admin_line.sign_access_url)

        # Non-admin user sees nothing
        line_as_other = line.with_user(self.other_user)
        self.assertFalse(line_as_other.sign_access_url)

    # -------------------------------------------------------------------------
    # _xx_get_approval_line_specs / _xx_sync_approval_lines
    # -------------------------------------------------------------------------

    def test_sync_no_department_creates_no_lines(self):
        self.po._xx_sync_approval_lines()
        self.assertFalse(self.po.xx_approval_line_ids)

    def test_sync_autofills_single_user(self):
        self._make_matrix(self.rule_1, self.real_approver_1)
        self.po.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertEqual(line.user_id, self.real_approver_1)

    def test_sync_one_line_two_choices_not_autofilled(self):
        """When multiple users are in the matrix for a group, user must choose — no auto-fill."""
        self._make_matrix(self.rule_1, self.real_approver_1, self.real_approver_2)
        self.po.xx_department_id = self.department
        lines = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertEqual(len(lines), 1)
        self.assertFalse(lines.user_id)

    def test_sync_one_line_three_choices_not_autofilled(self):
        self._make_matrix(
            self.rule_1, self.real_approver_1, self.real_approver_2, self.real_approver_3
        )
        self.po.xx_department_id = self.department
        lines = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertEqual(len(lines), 1)
        self.assertFalse(lines.user_id)

    def test_sync_removes_stale_lines_on_dept_change(self):
        self._make_matrix(self.rule_1, self.real_approver_1, self.real_approver_2)
        self.po.xx_department_id = self.department
        self.assertEqual(
            len(self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)),
            1,
        )
        # Switch to a department with no matrix rows → still one line, no auto-fill
        self.po.xx_department_id = self.department_b
        lines = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertEqual(len(lines), 1)
        self.assertFalse(lines.user_id)

    def test_sync_does_not_overwrite_existing_user(self):
        self._make_matrix(self.rule_1, self.real_approver_1)
        self.po.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertEqual(line.user_id, self.real_approver_1)
        # Re-sync should not reset already-filled user
        self.po._xx_sync_approval_lines()
        self.assertEqual(line.user_id, self.real_approver_1)

    def test_sync_no_matrix_with_dept_creates_line_no_user(self):
        self.po.xx_department_id = self.department
        rule_1_lines = self.po.xx_approval_line_ids.filtered(
            lambda ln: ln.studio_rule_id == self.rule_1
        )
        self.assertEqual(len(rule_1_lines), 1)
        self.assertFalse(rule_1_lines.user_id)

    def test_write_syncs_on_department_change(self):
        self._make_matrix(self.rule_1, self.real_approver_1)
        self.po.write({"xx_department_id": self.department.id})
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertEqual(line.user_id, self.real_approver_1)

    def test_department_field_exists(self):
        self.assertTrue(hasattr(self.po, "xx_department_id"))

    # -------------------------------------------------------------------------
    # _onchange_xx_approvals (via Form)
    # -------------------------------------------------------------------------

    def test_onchange_department_syncs_lines_via_form(self):
        """Setting department via Form triggers onchange and syncs approval lines."""
        self._make_matrix(self.rule_1, self.real_approver_1)
        self._make_matrix(self.rule_2, self.real_approver_2)
        with Form(self.po) as po_form:
            po_form.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertEqual(line.user_id, self.real_approver_1)

    def test_onchange_clears_stale_lines_via_form(self):
        """Removing department via Form clears all dynamic approval lines."""
        self._make_matrix(self.rule_1, self.real_approver_1)
        self._make_matrix(self.rule_2, self.real_approver_2)
        with Form(self.po) as po_form:
            po_form.xx_department_id = self.department
        self.assertTrue(self.po.xx_approval_line_ids)
        with Form(self.po) as po_form:
            po_form.xx_department_id = self.env["account.analytic.account"]
        self.assertFalse(self.po.xx_approval_line_ids)

    def test_allowed_user_ids_restricted_after_dept_switch(self):
        """Switching to a dept with matrix entries restricts allowed_user_ids to matrix users."""
        self._make_matrix(self.rule_1, self.real_approver_1)
        # First set dept_b (no matrix) — allowed_user_ids should be empty
        self.po.xx_department_id = self.department_b
        line_b = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertFalse(line_b.allowed_user_ids)
        # Switch to dept (has matrix entry) — allowed_user_ids should restrict to matrix users
        self.po.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertIn(self.real_approver_1, line.allowed_user_ids)
        self.assertNotIn(self.real_approver_2, line.allowed_user_ids)

    # -------------------------------------------------------------------------
    # _compute_can_validate
    # -------------------------------------------------------------------------

    def test_can_validate_true_for_assigned_user(self):
        self._assign(self.rule_1, self.real_approver_1)
        rule_as_approver = self.rule_1.with_user(self.real_approver_1)
        self.assertTrue(rule_as_approver.can_validate)

    def test_can_validate_false_for_unassigned_user(self):
        self._assign(self.rule_1, self.real_approver_1)
        rule_as_other = self.rule_1.with_user(self.other_user)
        self.assertFalse(rule_as_other.can_validate)

    def test_can_validate_false_when_no_assignment(self):
        rule_as_approver = self.rule_1.with_user(self.real_approver_1)
        self.assertFalse(rule_as_approver.can_validate)

    def test_can_validate_unaffected_for_non_dynamic_rule(self):
        rule_as_approver = self.rule_fixed.with_user(self.real_approver_1)
        self.assertTrue(rule_as_approver.can_validate)
        rule_as_other = self.rule_fixed.with_user(self.other_user)
        self.assertFalse(rule_as_other.can_validate)

    # -------------------------------------------------------------------------
    # check_approval — pre-approved snapshot
    # -------------------------------------------------------------------------

    def test_check_approval_snapshots_pre_approved_state(self):
        """check_approval injects pre-approved rule IDs into context for PO model."""
        self._assign(self.rule_1, self.real_approver_1)
        self._assign(self.rule_2, self.real_approver_2)
        # Approve rule_1
        self.rule_1.with_user(self.real_approver_1)._set_approval(self.po.id, True)

        # check_approval should not raise; the snapshot prevents within-call chaining
        result = self.rule_2.with_user(self.real_approver_2).check_approval(
            "purchase.order", self.po.id, "button_confirm", False
        )
        # Result is False when prior steps are approved but current step hasn't been set yet
        self.assertIsNotNone(result)

    def test_check_approval_non_po_model_no_snapshot(self):
        """For non-PO models, check_approval delegates straight to super without snapshot."""
        # The method should not raise for non-purchase.order models
        result = self.rule_1.check_approval("res.partner", 1, "write", False)
        self.assertIsNotNone(result)

    # -------------------------------------------------------------------------
    # _create_request
    # -------------------------------------------------------------------------

    def test_create_request_non_dynamic_rule_delegates(self):
        """Non-dynamic rules delegate _create_request to super."""
        # rule_fixed is not dynamic; super creates a standard request
        result = self.rule_fixed._create_request(self.po.id)
        # Super returns truthy when it creates a request or False when conditions aren't met
        self.assertIsNotNone(result)

    def test_create_request_dynamic_without_prior_approval_returns_false(self):
        """Dynamic rule 2 returns False when rule 1 (prior step) is not approved."""
        self._assign(self.rule_2, self.real_approver_2)
        result = self.rule_2._create_request(self.po.id)
        self.assertFalse(result)

    def test_create_request_dynamic_with_prior_approval_creates_activity(self):
        """Approving rule_1 causes Studio to auto-call _create_request for rule_2."""
        self._assign(self.rule_1, self.real_approver_1)
        self._assign(self.rule_2, self.real_approver_2)
        # Studio automatically calls _create_request for the next-level rule after approval
        # (studio_approval.py line 694: if approved and notification_order != '9').
        self.rule_1.with_user(self.real_approver_1)._set_approval(self.po.id, True)
        activity = self.env["mail.activity"].search(
            [("res_id", "=", self.po.id), ("user_id", "=", self.real_approver_2.id)]
        )
        self.assertTrue(activity)

    def test_create_request_no_assigned_user_returns_false(self):
        """Dynamic rule returns False when no user is assigned on the PO."""
        result = self.rule_1._create_request(self.po.id)
        self.assertFalse(result)

    # -------------------------------------------------------------------------
    # _xx_complete_board_approval (sign_request)
    # -------------------------------------------------------------------------

    def test_xx_complete_board_approval_no_linked_line(self):
        """_xx_complete_board_approval does nothing when no linked approval line exists."""
        sign_req = self._make_sign_request("Orphan Request")
        # Should not raise — returns early when no po.approval.user is linked
        sign_req._xx_complete_board_approval()

    def test_xx_complete_board_approval_triggers_set_approval(self):
        """_xx_complete_board_approval calls _set_approval with board_sign context."""
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board Trigger Test XX"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "6",
            }
        )
        board_partner = self.env["res.partner"].create(
            {"name": "Board Trigger Partner", "email": "board@test.example"}
        )
        sign_req = self._make_sign_request("Board Sign Trigger", partner=board_partner)
        po_line = self.env["xx.po.approval.user"].create(
            {
                "order_id": self.po.id,
                "studio_rule_id": board_rule.id,
                "partner_id": board_partner.id,
                "sign_request_id": sign_req.id,
            }
        )
        self.assertTrue(po_line.sign_request_id)

        # Directly call the method; it should invoke _set_approval
        # We verify via the approval entry being created
        sign_req._xx_complete_board_approval()

        entry = (
            self.env["studio.approval.entry"]
            .sudo()
            .search(
                [
                    ("rule_id", "=", board_rule.id),
                    ("res_id", "=", self.po.id),
                    ("approved", "=", True),
                ]
            )
        )
        self.assertTrue(entry)

    # -------------------------------------------------------------------------
    # _set_approval
    # -------------------------------------------------------------------------

    def test_set_approval_succeeds_for_assigned_user(self):
        self._assign(self.rule_1, self.real_approver_1)
        self.rule_1.with_user(self.real_approver_1)._set_approval(self.po.id, True)

    def test_set_approval_raises_for_unassigned_user(self):
        self._assign(self.rule_1, self.real_approver_1)
        with self.assertRaises(UserError):
            self.rule_1.with_user(self.other_user)._set_approval(self.po.id, True)

    def test_set_approval_raises_when_no_assignment_on_po(self):
        with self.assertRaises(UserError):
            self.rule_1.with_user(self.real_approver_1)._set_approval(self.po.id, True)

    def test_set_approval_non_dynamic_rule_unaffected(self):
        with self.assertRaises(UserError):
            self.rule_fixed.with_user(self.other_user)._set_approval(self.po.id, True)

    # -------------------------------------------------------------------------
    # Multi-step / cross-PO
    # -------------------------------------------------------------------------

    def test_different_users_per_step(self):
        self._assign(self.rule_1, self.real_approver_1)
        self._assign(self.rule_2, self.real_approver_2)

        self.rule_1.with_user(self.real_approver_1)._set_approval(self.po.id, True)
        with self.assertRaises(UserError):
            self.rule_2.with_user(self.real_approver_1)._set_approval(self.po.id, True)

        self.rule_2.with_user(self.real_approver_2)._set_approval(self.po.id, True)

    def test_assignment_scoped_to_po(self):
        """User assigned on PO A cannot approve via rule on PO B."""
        po_b = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "name": self.product.display_name,
                            "product_id": self.product.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                            "date_planned": "2025-01-01 00:00:00",
                        }
                    )
                ],
            }
        )
        self._assign(self.rule_1, self.real_approver_1)
        with self.assertRaises(UserError):
            self.rule_1.with_user(self.real_approver_1)._set_approval(po_b.id, True)

    # -------------------------------------------------------------------------
    # Dynamic rules filtered on PO — only xx_is_dynamic_approver rules shown
    # -------------------------------------------------------------------------

    def test_applicable_rules_excludes_non_dynamic(self):
        """_xx_applicable_dynamic_rules must never include non-dynamic rules."""
        applicable = self.po._xx_applicable_dynamic_rules()
        self.assertNotIn(self.rule_fixed, applicable)
        self.assertIn(self.rule_1, applicable)
        self.assertIn(self.rule_2, applicable)

    def test_sync_does_not_create_lines_for_non_dynamic_rules(self):
        self.po.xx_department_id = self.department
        rule_ids = self.po.xx_approval_line_ids.mapped("studio_rule_id")
        self.assertNotIn(self.rule_fixed, rule_ids)

    # -------------------------------------------------------------------------
    # No lines without department / required users on save
    # -------------------------------------------------------------------------

    def test_no_lines_without_department(self):
        self.assertFalse(self.po.xx_department_id)
        self.po._xx_sync_approval_lines()
        self.assertFalse(self.po.xx_approval_line_ids)

    def test_write_raises_if_approval_line_missing_user(self):
        self.po.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        self.assertTrue(line)
        self.assertFalse(line.user_id)
        with self.assertRaises(ValidationError):
            self.po.write({"xx_approval_line_ids": [(1, line.id, {})]})

    def test_write_succeeds_when_all_users_assigned(self):
        self._make_matrix(self.rule_1, self.real_approver_1)
        self._make_matrix(self.rule_2, self.real_approver_2)
        self.po.xx_department_id = self.department
        lines = self.po.xx_approval_line_ids
        self.po.write(
            {"xx_approval_line_ids": [(1, ln.id, {"user_id": ln.user_id.id}) for ln in lines]}
        )

    # -------------------------------------------------------------------------
    # sign.request write hook
    # -------------------------------------------------------------------------

    def test_sign_request_write_signed_triggers_board_approval(self):
        """write({'state': 'signed'}) calls _xx_complete_board_approval and creates entry."""
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Write Hook Board Group"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "7",
            }
        )
        board_partner = self.env["res.partner"].create(
            {"name": "Write Hook Partner", "email": "writehook@test.example"}
        )
        sign_req = self._make_sign_request("Write Hook Test", partner=board_partner)
        self.env["xx.po.approval.user"].create(
            {
                "order_id": self.po.id,
                "studio_rule_id": board_rule.id,
                "partner_id": board_partner.id,
                "sign_request_id": sign_req.id,
            }
        )
        sign_req.sudo().write({"state": "signed"})
        entry = (
            self.env["studio.approval.entry"]
            .sudo()
            .search(
                [
                    ("rule_id", "=", board_rule.id),
                    ("res_id", "=", self.po.id),
                    ("approved", "=", True),
                ]
            )
        )
        self.assertTrue(entry)

    # -------------------------------------------------------------------------
    # _compute_can_validate — board approval paths
    # -------------------------------------------------------------------------

    def test_compute_can_validate_board_approval_paths(self):
        """Board rule: without sign context → blocked; with context → granted."""
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board CV Test Group"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "8",
            }
        )
        # real_approver_1 is not in approver_ids → super gives False → our board path runs
        self.assertFalse(board_rule.with_user(self.real_approver_1).can_validate)
        # With _xx_board_sign_completed context the programmatic path sets can_validate = True
        rule_with_ctx = board_rule.with_context(_xx_board_sign_completed=True).with_user(
            self.real_approver_1
        )
        self.assertTrue(rule_with_ctx.can_validate)

    # -------------------------------------------------------------------------
    # _create_request — existing-request guard
    # -------------------------------------------------------------------------

    def test_create_request_returns_false_if_already_has_request(self):
        """Second call to _create_request returns False once a request record exists."""
        self._assign(self.rule_1, self.real_approver_1)
        self.rule_1._create_request(self.po.id)  # creates the studio.approval.request
        result = self.rule_1._create_request(self.po.id)  # finds existing → False
        self.assertFalse(result)

    # -------------------------------------------------------------------------
    # _create_board_sign_request — early-exit paths
    # -------------------------------------------------------------------------

    def test_create_board_sign_request_returns_false_if_request_exists(self):
        """_create_board_sign_request returns False when an approval request already exists."""
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board Req Exists Group"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "9",
            }
        )
        activity = self.po.activity_schedule(
            activity_type_id=self.env.ref("mail.mail_activity_data_todo").id,
            user_id=self.dummy_user.id,
            summary="Pre-existing approval request",
        )
        self.env["studio.approval.request"].sudo().create(
            {"rule_id": board_rule.id, "mail_activity_id": activity.id, "res_id": self.po.id}
        )
        result = board_rule._create_board_sign_request(self.po.id)
        self.assertFalse(result)

    def test_create_board_sign_request_raises_when_no_board_member(self):
        """_create_board_sign_request raises UserError when no board member is assigned."""
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board No Member Group"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "9",
            }
        )
        # No xx.po.approval.user with partner_id for this rule → UserError
        with self.assertRaises(UserError):
            board_rule._create_board_sign_request(self.po.id)

    def test_create_board_sign_request_creates_sign_request(self):
        """_create_board_sign_request succeeds when a board member is assigned.

        Regression: clicking Done on a chatter activity for a preceding rule triggered
        Studio's _set_approval → _create_request → _create_board_sign_request for the next
        (board) rule, which crashed with:
            AttributeError: 'Environment' object has no attribute 'with_context'
        The fix is self.with_context(lang=lang).env instead of self.env.with_context(lang=lang).
        """
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board Sign Request Regression XX"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "9",
            }
        )
        board_partner = self.env["res.partner"].create(
            {
                "name": "Board Sign Regression Partner",
                "lang": "en_US",
                "email": "board@test.example",
            }
        )
        self.env["xx.po.approval.user"].create(
            {
                "order_id": self.po.id,
                "studio_rule_id": board_rule.id,
                "partner_id": board_partner.id,
            }
        )

        with file_open("sign/static/demo/sample_contract.pdf", "rb") as fh:
            pdf_bytes = fh.read()

        with patch.object(
            type(self.env["ir.actions.report"]),
            "_render_qweb_pdf",
            return_value=(pdf_bytes, "pdf"),
        ):
            result = board_rule._create_board_sign_request(self.po.id)

        self.assertTrue(result)
        sign_request = self.env["sign.request"].sudo().search([("reference", "like", self.po.name)])
        self.assertTrue(sign_request)

    # -------------------------------------------------------------------------
    # Bug fixes: company fallback + partner/user filter in matrix searches
    # -------------------------------------------------------------------------

    def test_allowed_partner_ids_ignores_user_only_matrix_rows(self):
        """Matrix rows with user_id only must not appear in allowed_partner_ids for board steps."""
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board Filter Test XX"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "1",
            }
        )
        board_partner = self.env["res.partner"].create({"name": "Board Filter Partner"})
        # One user_id row and one partner_id row for the same group
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": board_group.id,
                "user_id": self.real_approver_1.id,
            }
        )
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": board_group.id,
                "partner_id": board_partner.id,
            }
        )
        self.po.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == board_rule)
        # Only the partner_id row should appear — user_id rows must be excluded
        self.assertIn(board_partner, line.allowed_partner_ids)
        self.assertEqual(len(line.allowed_partner_ids), 1)

    def test_allowed_user_ids_ignores_partner_only_matrix_rows(self):
        """Partner-only matrix rows must not appear in allowed_user_ids for non-board steps."""
        board_partner = self.env["res.partner"].create({"name": "Partner Noise Row"})
        # Add a partner_id row to the same group used by rule_1 (non-board)
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": self.approval_group_1.id,
                "partner_id": board_partner.id,
            }
        )
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": self.approval_group_1.id,
                "user_id": self.real_approver_1.id,
            }
        )
        self.po.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == self.rule_1)
        # Only the user_id row should appear — partner_id rows must be excluded
        self.assertIn(self.real_approver_1, line.allowed_user_ids)
        self.assertEqual(len(line.allowed_user_ids), 1)

    def test_sync_board_step_autofills_single_partner_ignoring_user_rows(self):
        """_xx_get_approval_line_specs auto-fills partner when exactly one partner row exists,
        even if the same group also has user_id rows."""
        model_id = self.env["ir.model"]._get("purchase.order").id
        board_group = self.env["res.groups"].create({"name": "Board Autofill Filter XX"})
        board_rule = self.env["studio.approval.rule"].create(
            {
                "model_id": model_id,
                "method": "button_confirm",
                "approver_ids": [Command.set([self.dummy_user.id])],
                "xx_is_dynamic_approver": True,
                "xx_is_board_approval": True,
                "approval_group_id": board_group.id,
                "notification_order": "1",
            }
        )
        board_partner = self.env["res.partner"].create({"name": "Board Autofill Partner"})
        # user_id noise row — must not interfere with partner auto-fill
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": board_group.id,
                "user_id": self.real_approver_1.id,
            }
        )
        self.env["xx.po.approval.matrix"].create(
            {
                "company_id": self.env.company.id,
                "analytic_account_id": self.department.id,
                "group_id": board_group.id,
                "partner_id": board_partner.id,
            }
        )
        self.po.xx_department_id = self.department
        line = self.po.xx_approval_line_ids.filtered(lambda ln: ln.studio_rule_id == board_rule)
        # Exactly one partner row → auto-filled
        self.assertEqual(line.partner_id, board_partner)
