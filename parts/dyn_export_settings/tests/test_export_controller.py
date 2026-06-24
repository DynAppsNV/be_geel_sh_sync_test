import fnmatch
import io
import json
import xml.etree.ElementTree as etree
import zipfile

from .test_export_common import TestExportSettingsCommonController


class TestExportController(TestExportSettingsCommonController):
    def test_10_download(self):  # noqa: C901
        self.authenticate("admin", "admin")
        export_settings = self.url_open(
            f"/web/dynapps/settings/download/{self.wizard.id}", timeout=60
        )
        export_settings.raise_for_status()
        self.assertEqual(export_settings.status_code, 200)
        self.assertTrue(export_settings.content.startswith(b"PK"))  # check if zip file
        zip_file = zipfile.ZipFile(io.BytesIO(export_settings.content))

        self.assertIn("parts/custom/xx_base/data/res_lang_data.xml", zip_file.namelist())
        self.assertIn(
            "parts/custom/xx_base/data/res_config_settings_data.xml",
            zip_file.namelist(),
        )
        self.assertIn("parts/custom/xx_base/data/res_partner_data.xml", zip_file.namelist())
        self.assertIn("parts/custom/xx_base/data/res_company_data.xml", zip_file.namelist())
        excluded = [
            "parts/custom/xx_base/__manifest__.py",
            "parts/custom/xx_base_extra/__manifest__.py",
            "parts/custom/xx_base_extra_date/__manifest__.py",
            "parts/custom/xx_base_extra_html/__manifest__.py",
            "dyn-build.yaml",
        ]
        for file_name in zip_file.namelist():
            with zip_file.open(file_name) as file:
                content = file.read()
                self.assertTrue(content)
                if file_name in excluded or fnmatch.fnmatch(
                    file_name, "parts/custom/xx_base/static/img/*.png"
                ):
                    continue
                content_decoded = content.decode()
                self.assertIn(
                    file_name,
                    [
                        "parts/custom/xx_base/data/res_lang_data.xml",
                        "parts/custom/xx_base/data/res_config_settings_data.xml",
                        "parts/custom/xx_base/data/res_partner_data.xml",
                        "parts/custom/xx_base/data/res_company_data.xml",
                        "parts/custom/xx_base_extra/data/res_partner_data.xml",
                        "parts/custom/xx_base_extra_html/data/res_partner_data.xml",
                    ],
                )
                if '<?xml version="1.0" encoding="UTF-8" ?>' in content_decoded:
                    root = etree.fromstring(content_decoded)
                    if file_name == "parts/custom/xx_base/data/res_config_settings_data.xml":
                        functions = root.findall("function")
                        self.assertTrue(functions)
                        function_names = [function.attrib.get("name") for function in functions]
                        self.assertTrue("create" in function_names)
                        self.assertTrue("execute" in function_names)
                        for function in functions:
                            if function.get("name") == "create":
                                self.assertTrue(function.get("model") == "res.config.settings")
                                self.assertIn(
                                    "'show_effect': True",
                                    function.find(".//value[@eval]").get("eval"),
                                )
                                self.assertIn(
                                    "'xx_base_module_name': 'xx_base'",
                                    function.find(".//value[@eval]").get("eval"),
                                )
                    elif file_name == "parts/custom/xx_base_extra_html/data/res_partner_data.xml":
                        records = root.findall("record")
                        self.assertFalse(records)
                        functions = root.findall("function")
                        self.assertTrue(functions)
                        function_names = [function.attrib.get("name") for function in functions]
                        self.assertTrue("_dyn_export_update_translations" in function_names)
                        for function in functions:
                            if function.get("name") == "_dyn_export_update_translations":
                                self.assertTrue(function.get("model") == "res.partner")
                                self.assertIn(
                                    "ref('dyn_export_settings.base_partner')",
                                    function.find(".//value[@eval]").get("eval"),
                                )
                                value_cdata = function.findall(".//value")[-1]
                                translations = json.loads(value_cdata.text.strip())
                                self.assertEqual(
                                    translations["xx_new_field_html"]["en_US"], "<p>English</p>"
                                )
                                self.assertEqual(
                                    translations["xx_new_field_html"]["nl_BE"], "<p>Dutch</p>"
                                )
                    else:
                        records = root.findall("record")
                        self.assertTrue(records)
                        if file_name == "parts/custom/xx_base/data/res_lang_data.xml":
                            record_ids = [record.attrib.get("id") for record in records]
                            self.assertTrue("base_language_install" in record_ids)
                            self.assertTrue("base.lang_en" in record_ids)
                            self.assertTrue("base.lang_nl_BE" in record_ids)
                            for record in records:
                                if record.get("id") == "base_language_install":
                                    self.assertTrue(record.get("model") == "base.language.install")
                                elif record.get("id") == "base.lang_nl_BE":
                                    self.assertTrue(record.get("model") == "res.lang")
                                    self.assertEqual(
                                        record.find(".//field[@name='name']").text,
                                        "Dutch (BE) / Nederlands (BE)",
                                    )
                                elif record.get("id") == "base.lang_en":
                                    self.assertTrue(record.get("model") == "res.lang")
                                    self.assertEqual(
                                        record.find(".//field[@name='name']").text, "English (US)"
                                    )
                        elif file_name == "parts/custom/xx_base/data/res_partner_data.xml":
                            record_ids = [record.attrib.get("id") for record in records]
                            self.assertTrue("base.main_partner" in record_ids)
                            self.assertTrue("dyn_export_settings.base_partner" in record_ids)
                            for record in records:
                                if record.get("id") == "base.main_partner":
                                    self.assertTrue(record.get("model") == "res.partner")
                                    self.assertEqual(
                                        record.find(".//field[@name='name']").text, "YourCompany"
                                    )
                                    self.assertIsNone(record.find(".//field[@name='xx_new_field']"))
                                elif record.get("id") == "dyn_export_settings.base_partner":
                                    self.assertTrue(record.get("model") == "res.partner")
                                    self.assertEqual(
                                        record.find(".//field[@name='name']").text, "Base Company"
                                    )
                                    self.assertIsNone(record.find(".//field[@name='xx_new_field']"))
                                self.assertIsNone(record.find(".//field[@name='x_studio_field']"))
                                self.assertIsNotNone(
                                    record.find(
                                        ".//field[@name='xx_new_field_properties_definition']"
                                    )
                                )
                                self.assertIsNone(
                                    record.find(".//field[@name='xx_new_field_properties']")
                                )
                        elif file_name == "parts/custom/xx_base/data/res_company_data.xml":
                            record_ids = [record.attrib.get("id") for record in records]
                            self.assertTrue("base.main_company" in record_ids)
                            self.assertTrue("dyn_export_settings.base_company" in record_ids)
                            self.assertTrue("base.user_root" in record_ids)
                            self.assertTrue("base.user_admin" in record_ids)
                            self.assertTrue(
                                self._check_currency(root, "base.main_company", "base.USD")
                            )
                            for record in records:
                                if record.get("id") == "base.main_company":
                                    self.assertTrue(record.get("model") == "res.company")
                                    self.assertEqual(
                                        record.find(".//field[@name='partner_id']").get("ref"),
                                        "base.main_partner",
                                    )
                                    self.assertFalse(record.find(".//field[@name='currency_id']"))
                                    self.assertFalse(
                                        record.find(".//field[@name='profiling_enabled_until']")
                                    )
                                elif record.get("id") == "dyn_export_settings.base_company":
                                    self.assertTrue(record.get("model") == "res.company")
                                    self.assertEqual(
                                        record.find(".//field[@name='partner_id']").get("ref"),
                                        "dyn_export_settings.base_partner",
                                    )
                                    self.assertFalse(
                                        record.find(".//field[@name='profiling_enabled_until']")
                                    )
                                    self.assertEqual(
                                        record.find(".//field[@name='currency_id']").get("ref"),
                                        "base.EUR",
                                    )
                                elif record.get("id") == "base.user_root":
                                    self.assertTrue(record.get("model") == "res.users")
                                    self.assertIn(
                                        "Command.link(ref('dyn_export_settings.base_company'))",
                                        record.find(".//field[@name='company_ids']").get("eval"),
                                    )
                                elif record.get("id") == "base.user_admin":
                                    self.assertTrue(record.get("model") == "res.users")
                                    self.assertIn(
                                        "Command.link(ref('dyn_export_settings.base_company'))",
                                        record.find(".//field[@name='company_ids']").get("eval"),
                                    )
                            self.assertTrue(
                                self._check_translations(
                                    root,
                                    "dyn_export_settings.base_company",
                                    "report_header",
                                )
                            )
                        elif file_name == "parts/custom/xx_base_extra/data/res_partner_data.xml":
                            record_ids = [record.attrib.get("id") for record in records]
                            self.assertTrue("base.main_partner" in record_ids)
                            self.assertTrue("dyn_export_settings.base_partner" in record_ids)
                            for record in records:
                                if record.get("id") == "base.main_partner":
                                    self.assertTrue(record.get("model") == "res.partner")
                                    self.assertIsNotNone(
                                        record.find(".//field[@name='xx_new_field']")
                                    )
                                elif record.get("id") == "dyn_export_settings.base_partner":
                                    self.assertTrue(record.get("model") == "res.partner")
                                    self.assertIsNotNone(
                                        record.find(".//field[@name='xx_new_field']")
                                    )
                                self.assertIsNone(record.find(".//field[@name='x_studio_field']"))
        zip_file.close()
