from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import new_test_user


class TestRule(TransactionCase):
    def test_secret(self):
        # Reconfirm since we disable auditlog tests for testing
        rule = self.env.ref("xx_base.auditlog_rule_res_users")
        rule.with_context(test_enable_auditlog=True).set_to_confirmed()

        user = new_test_user(self.env, login="Pou", password="Secret_123_&")
        auditlog_log_pwd = self.env["auditlog.log.line"].search(
            [
                ("log_id.model_model", "=", user._name),
                ("log_id.res_id", "=", user.id),
                ("field_id.name", "=", "password"),
            ]
        )
        self.assertTrue(auditlog_log_pwd)
        self.assertEqual(auditlog_log_pwd.new_value, "********")
        self.assertEqual(auditlog_log_pwd.new_value_text, "********")
        user.password = "New_secret_123_&"
        auditlog_log_new_pwd = self.env["auditlog.log.line"].search(
            [
                ("log_id.model_model", "=", user._name),
                ("log_id.res_id", "=", user.id),
                ("field_id.name", "=", "password"),
                ("id", "!=", auditlog_log_pwd.id),
            ]
        )
        self.assertTrue(auditlog_log_new_pwd)
        self.assertEqual(auditlog_log_new_pwd.new_value, "********")
        self.assertEqual(auditlog_log_new_pwd.new_value_text, "********")

        # Reset rule to draft
        rule.set_to_draft()
