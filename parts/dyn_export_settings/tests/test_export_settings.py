from unittest.mock import patch

from odoo.exceptions import MissingError, ValidationError
from odoo.tests import mute_logger, tagged

from odoo.addons.dyn_export_settings.models.dyn_export_settings_mixin import DynExportSettingsMixin

from .test_export_common import TestExportSettingsCommon


class TestExportSettings(TestExportSettingsCommon):
    def test_00_base_module_name(self):
        self.assertEqual(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("dyn_export_settings.base_module_name"),
            "xx_base",
        )
        config = self.env["res.config.settings"].create(
            {
                "xx_base_module_name": "other_module",
            }
        )
        config.execute()
        self.assertEqual(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("dyn_export_settings.base_module_name"),
            "other_module",
        )

    def test_10_computed_fields(self):
        lang_data = self.wizard.module_data_ids.filtered(lambda r: r.model == "res.lang")
        self.assertIn("Command.link(ref('base.lang_en'))", lang_data.settings_tech)
        self.assertIn("Command.link(ref('base.lang_nl_BE'))", lang_data.settings_tech)
        self.assertIn("Command.link(ref('base.lang_en'))", lang_data.settings_tech_diff)
        self.assertIn("Command.link(ref('base.lang_nl_BE'))", lang_data.settings_tech_diff)
        self.assertEqual(
            "en_US - English (US)\nnl_BE - Dutch (BE) / Nederlands (BE)", self.wizard.languages_func
        )

        # test disabled modules
        self.assertTrue(self.wizard.disabled_modules_tech)
        self.assertIn("partner_autocomplete", self.wizard.disabled_modules_tech)
        self.assertTrue(self.wizard.disabled_modules_settings_func)
        self.assertIn("partner_autocomplete", self.wizard.disabled_modules_settings_func)
        self.assertFalse(self.wizard.disabled_modules_func)

        self.assertTrue(self.wizard.settings_func)

        # test company settings
        self.assertTrue(self.wizard.company_settings_func)
        self.assertIn("Base Company", self.wizard.company_settings_func)

        self.assertEqual(
            self.test_company.get_external_id()[self.test_company.id],
            "dyn_export_settings.res_company_test_company",
        )
        self.assertEqual(
            self.test_company.partner_id.get_external_id()[self.test_company.partner_id.id],
            "dyn_export_settings.res_partner_test_company",
        )

        # test company partner logos
        self.env["ir.config_parameter"].sudo().set_param(
            "dyn_export_settings.base_module_name", "dyn_export_settings"
        )
        self.assertTrue(self.wizard.partner_logo_ids)
        main_company_partner_logo = self.wizard.partner_logo_ids.filtered(
            lambda r: r.partner_id == self.env.ref("base.main_company").partner_id
        )
        self.assertEqual(main_company_partner_logo.filename, "main_partner.png")
        self.assertTrue(main_company_partner_logo.logo_diff)
        base_company_partner_logo = self.wizard.partner_logo_ids.filtered(
            lambda r: r.partner_id == self.base_company.partner_id
        )
        self.assertEqual(base_company_partner_logo.filename, "base_partner.png")
        self.assertFalse(base_company_partner_logo.logo_diff)
        test_company_partner_logo = self.wizard.partner_logo_ids.filtered(
            lambda r: r.partner_id == self.test_company.partner_id
        )
        self.assertEqual(test_company_partner_logo.filename, "res_partner_test_company.png")
        self.assertTrue(test_company_partner_logo.logo_diff)
        self.assertFalse(test_company_partner_logo.original_logo)

        # Test custom fields
        self.assertTrue(self.wizard.custom_field_ids)
        new_field = self.wizard.custom_field_ids.filtered(
            lambda r: r.field_ids.name == "xx_new_field"
        )
        self.assertTrue(new_field)
        self.assertEqual(new_field.module_name, "xx_base_extra")
        partner_model = self.env.ref("base.model_res_partner")
        self.assertEqual(new_field.model_name, f"{partner_model.model} ({partner_model.name})")
        module_xx_base_extra = self.env.ref("base.module_xx_base_extra")
        module_xx_base_extra.shortdesc = "Test"
        self.wizard.custom_field_ids.invalidate_recordset()
        self.assertEqual(
            new_field.module_name, f"{module_xx_base_extra.name} ({module_xx_base_extra.shortdesc})"
        )

        self.wizard.partner_logo_ids.invalidate_recordset()
        with patch.object(DynExportSettingsMixin, "_get_attachment", return_value=None):
            test_company_partner_logo = self.wizard.partner_logo_ids.filtered(
                lambda r: r.partner_id == self.test_company.partner_id
            )
            self.assertEqual(test_company_partner_logo.filename, "res_partner_test_company.png")

    def test_11_install_disabled_module(self):
        with self.assertRaisesRegex(
            ValidationError, "Module 'partner_autocomplete' is set to be disabled"
        ):
            self.env["ir.module.module"].search(
                [("name", "=", "partner_autocomplete")]
            ).button_install()

    @mute_logger("odoo.addons.dyn_export_settings.models.res_company")
    def test_20_company_methods(self):
        self.base_company._dyn_export_fix_currency(self.env.ref("base.EUR"))
        with self.assertRaisesRegex(MissingError, "Record does not exist or has been deleted"):
            self.base_company._dyn_export_fix_currency(-9999, raise_exception=True)

    def test_30_generate_xml_ids(self):
        partner = (
            self.env["res.partner"]
            .with_context(install_mode=True, install_model="res.partner")
            .create({"name": "Test Company without XML ID"})
        )
        company = (
            self.env["res.company"]
            .with_context(install_mode=True, install_model="res.company")
            .create({"name": "Test Company without XML ID", "partner_id": partner.id})
        )

        self.assertFalse(partner.get_external_id()[partner.id])
        partner = self.env["res.partner"].browse(partner.id)
        self.assertFalse(partner.get_external_id()[partner.id])

        generated_xml_id = partner.export_data(["id"]).get("datas")[0][0]
        self.assertRegex(generated_xml_id, "__export__.res_partner_")
        self.assertEqual(partner.get_external_id()[partner.id], generated_xml_id)

        partner._dyn_export_add_xml_id(overwrite=True)
        self.assertTrue(partner.get_external_id()[partner.id])
        new_xml_id = partner.with_context(keep_original_xml_id=True)._dyn_export_get_xml_id()
        self.assertEqual(new_xml_id, "xx_base.res_partner_test_company_without_xml_id")
        self.assertEqual(partner.get_external_id()[partner.id], new_xml_id)

        self.assertFalse(company.get_external_id()[company.id])
        company = self.env["res.company"].browse(company.id)
        self.assertFalse(company.get_external_id()[company.id])

        generated_xml_id = company.export_data(["id"]).get("datas")[0][0]
        self.assertRegex(generated_xml_id, "__export__.res_company_")
        self.assertEqual(company.get_external_id()[company.id], generated_xml_id)

        company._dyn_export_add_xml_id(overwrite=True)
        self.assertTrue(company.get_external_id()[company.id])
        new_xml_id = company.with_context(keep_original_xml_id=True)._dyn_export_get_xml_id()
        self.assertEqual(new_xml_id, "xx_base.res_company_test_company_without_xml_id")
        self.assertEqual(company.get_external_id()[company.id], new_xml_id)


@tagged("post_install", "-at_install")
class TestExportSettingsPostInstall(TestExportSettingsCommon):
    def test_10_computed_fields(self):
        # test installed modules
        self.assertIn("base", self.wizard.installed_modules_func)
        self.assertIn("dyn_export_settings", self.wizard.installed_modules_func)
