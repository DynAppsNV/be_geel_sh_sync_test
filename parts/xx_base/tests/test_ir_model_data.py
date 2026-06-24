from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, patch
from odoo.tools import config


class TestIrModelData(TransactionCase):
    @patch.dict(config.options, {"test_force": True})
    def test_unlink_force(self):
        with self.assertRaisesRegex(
            ValidationError, "Data defined in customization cannot be deleted!"
        ):
            self.env.ref("xx_base.auditlog_rule_res_company").with_user(
                self.env.ref("base.user_demo")
            ).sudo().unlink()

    @patch.dict(config.options, {"test_force": True})
    def test_unlink(self):
        self.env.ref("xx_base.auditlog_rule_res_company").unlink()
