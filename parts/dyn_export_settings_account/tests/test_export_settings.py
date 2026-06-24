from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import mute_logger, tagged

from .test_export_common import TestExportAccountCommon


@tagged("post_install", "-at_install")
class TestExportSettings(TestExportAccountCommon):
    def test_10_computed_fields(self):
        self.assertIn("dyn_export_settings_account", self.wizard.installed_modules_func)

    def test_20_chart_template(self):
        self.base_company.chart_template = False
        self.base_company._dyn_export_load_chart_template("generic_coa")

    def _check_accounting_fields(self, model):
        model_obj = self.env[model]
        self.wizard._compute_settings()
        data = self.wizard.module_data_ids.filtered(
            lambda r: r.model == model and r.module_id == model_obj._dyn_export_get_base_module()
        )
        account_fields = [
            f.name
            for name, f in model_obj._fields.items()
            if f.relational and f.comodel_name.startswith("account")
        ]
        self.assertTrue(account_fields)
        self.assertTrue(data.settings_tech)
        for account_field in account_fields:
            self.assertNotIn(account_field, data.settings_tech)

    def test_30_res_config_account_fields(self):
        self._check_accounting_fields("res.config.settings")

    def test_40_res_company_account_fields(self):
        self._check_accounting_fields("res.company")

    def test_50_res_partner_account_fields(self):
        self._check_accounting_fields("res.partner")

    @mute_logger("odoo.addons.dyn_export_settings_account.models.res_company")
    def test_60_company_methods(self):
        self.base_company._dyn_export_fix_account_price_include("tax_excluded")
        self.env.ref("base.partner_demo").company_id = False
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.env.ref("base.partner_demo").id,
                "invoice_line_ids": [
                    Command.create({"name": "line1", "price_unit": 110.0}),
                ],
                "company_id": self.base_company.id,
            }
        )
        invoice.action_post()

        with self.assertRaisesRegex(
            ValidationError,
            "Cannot change Price Tax computation method on a company",
        ):
            self.base_company._dyn_export_fix_account_price_include(
                "tax_included", raise_exception=True
            )
