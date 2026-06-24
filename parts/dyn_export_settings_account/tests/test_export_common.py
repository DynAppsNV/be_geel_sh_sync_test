from odoo import Command

from odoo.addons.dyn_export_settings.tests.test_export_common import (
    TestExportSettingsCommon,
    TestExportSettingsCommonController,
)


class TestExportAccountCommon(TestExportSettingsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_module.write(
            {"dependencies_id": [Command.create({"name": "dyn_export_settings_account"})]}
        )

    def _check_company_function_data(self, root, method, company_ref, value):
        company = self.env.ref(company_ref)
        # Iterate through all <function> tags in the XML
        for function in root.findall(".//function"):
            # Check if the function matches the target model and method name
            if (
                function.attrib.get("model") == company._name
                and function.attrib.get("name") == method
                and function.findall(".//value")[0].get("eval") == f"ref('{company_ref}')"
            ):
                if isinstance(value, bool):
                    self.assertEqual(
                        function.findall(".//value")[1].get("eval"),
                        str(value),
                    )
                else:
                    self.assertEqual(function.findall(".//value")[1].text, value)
                return True
        return False


class TestExportAccountCommonController(
    TestExportSettingsCommonController, TestExportAccountCommon
):
    pass
