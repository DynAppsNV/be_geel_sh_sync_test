from lxml import etree as ET

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestExportFilterSelections(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Wizard = self.env["xx.dashboard.export.wizard"]

        # Create a dashboard
        self.dashboard = self.env["xx.dashboard"].create(
            {
                "name": "Test Dashboard for Export",
            }
        )

        # Create a custom filter for the dashboard
        self.custom_filter = self.env["xx.dyn.custom.filter"].create(
            {
                "filter_name": "Test Filter",
                "dashboard_id": self.dashboard.id,
                "use_odoo_data": False,
            }
        )

        # Add some manual selections to the filter
        self.selection1 = self.env["xx.dyn.custom.filter.selection"].create(
            {
                "filter_id": self.custom_filter.id,
                "name": "Selection 1",
                "value": "val1",
            }
        )

    def test_export_excludes_selection_ids(self):
        # Trigger export
        export_wizard = self.Wizard.create(
            {
                "export_items": [
                    Command.create({"name": self.dashboard.name, "res_id": self.dashboard.id})
                ]
            }
        )

        # We call export_model_data directly to get the XML string
        xml_data = export_wizard.export_model_data(self.env["xx.dashboard"], [self.dashboard.id])

        # Parse the XML
        root = ET.fromstring(xml_data)

        # Find the custom filter in the XML
        filter_elements = root.xpath("//xx_custom_filter_ids/*")
        self.assertTrue(filter_elements, "Custom filter should be exported")

        for filter_el in filter_elements:
            # Check for selection_ids or manual_selection_ids
            selections = filter_el.xpath("selection_ids")
            manual_selections = filter_el.xpath("manual_selection_ids")

            # According to issue, selection_ids should not be included
            self.assertFalse(selections, "selection_ids should NOT be included in the exported XML")
            self.assertFalse(
                manual_selections, "manual_selection_ids should NOT be included in the exported XML"
            )

            # Verify other fields are still there
            filter_name = filter_el.xpath("filter_name")
            self.assertTrue(filter_name, "filter_name should still be included")
            self.assertEqual(filter_name[0].text, "Test Filter")

    def test_repro_failure(self):
        # This is just to see if the test runs and fails if I change it
        pass
