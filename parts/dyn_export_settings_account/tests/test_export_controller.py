import io
import xml.etree.ElementTree as etree
import zipfile

from odoo.tests import tagged

from .test_export_common import TestExportAccountCommonController


@tagged("post_install", "-at_install")
class TestExportController(TestExportAccountCommonController):
    def test_10_download(self):
        self.authenticate("admin", "admin")
        export_settings = self.url_open(
            f"/web/dynapps/settings/download/{self.wizard.id}", timeout=60
        )
        export_settings.raise_for_status()
        zip_file = zipfile.ZipFile(io.BytesIO(export_settings.content))

        files2verify = [
            "parts/custom/xx_base/data/res_company_data.xml",
            "parts/custom/xx_base/data/res_config_settings_data.xml",
        ]
        for file_name in files2verify:
            self.assertIn(file_name, zip_file.namelist())
        for file_name in [f for f in zip_file.namelist() if f in files2verify]:
            with zip_file.open(file_name) as file:
                content = file.read()
                content_decoded = content.decode()
                root = etree.fromstring(content_decoded)
                if file_name == "parts/custom/xx_base/data/res_company_data.xml":
                    records = root.findall("record")
                    self.assertTrue(records)
                    self.assertTrue(
                        self._check_company_function_data(
                            root,
                            "_dyn_export_load_chart_template",
                            "base.main_company",
                            "generic_coa",
                        )
                    )
                    self.assertTrue(
                        self._check_company_function_data(
                            root,
                            "_dyn_export_fix_account_price_include",
                            "base.main_company",
                            "tax_excluded",
                        )
                    )
                    self.assertTrue(
                        self._check_company_function_data(
                            root,
                            "_dyn_export_fix_account_price_include",
                            "dyn_export_settings.base_company",
                            "tax_excluded",
                        )
                    )
                    for record in records:
                        if record.get("id") == "base.main_company":
                            self.assertTrue(record.get("model") == "res.company")
                            self.assertFalse(record.find(".//field[@name='chart_template']"))
                            self.assertFalse(record.find(".//field[@name='account_price_include']"))
                        elif record.get("id") == "dyn_export_settings.base_company":
                            self.assertTrue(record.get("model") == "res.company")
                            self.assertFalse(record.find(".//field[@name='chart_template']"))
                            self.assertFalse(record.find(".//field[@name='account_price_include']"))
                elif file_name == "parts/custom/xx_base/data/res_config_settings_data.xml":
                    functions = root.findall("function")
                    for function in functions:
                        if function.get("name") == "create":
                            self.assertTrue(function.get("model") == "res.config.settings")
                            self.assertIn(
                                "'group_fiscal_year': False",
                                function.find(".//value[@eval]").get("eval"),
                            )
        zip_file.close()
