from odoo import models
from odoo.tools import config


class AuditlogRule(models.Model):
    _inherit = "auditlog.rule"

    @staticmethod
    def _is_secret_field(field):
        secret_keywords = ["password", "passwd", "pwd", "secret", "token", "key"]
        return any(
            field.startswith(keyword) or f"_{keyword}" in field for keyword in secret_keywords
        )

    def _prepare_log_line_vals_on_write(self, log, field, old_values, new_values):
        if self._is_secret_field(field["name"]):
            if field.get("ttype") == "char":
                if isinstance(log, dict):
                    res_id = log["res_id"]
                else:
                    res_id = log.res_id
                old_values[res_id][field["name"]] = "********"
                new_values[res_id][field["name"]] = "********"
        return super()._prepare_log_line_vals_on_write(log, field, old_values, new_values)

    def _prepare_log_line_vals_on_create(self, log, field, new_values):
        if self._is_secret_field(field["name"]):
            if field.get("ttype") == "char":
                if isinstance(log, dict):
                    res_id = log["res_id"]
                else:
                    res_id = log.res_id
                new_values[res_id][field["name"]] = "********"
        return super()._prepare_log_line_vals_on_create(log, field, new_values)

    def _register_hook(self):
        """
        We don't want to enable auditlogging when running test-cases. Why? Because this would block
        certain write, create, unlink, read functions from being executed.
        """
        if not self.env.context.get("test_enable_auditlog") and (
            bool(config["test_enable"] or config["test_file"])
        ):
            return False

        return super()._register_hook()
