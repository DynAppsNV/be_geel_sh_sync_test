from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestDynDashboardExportCustom(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Dashboard = self.env["xx.dashboard"]
        self.Wizard = self.env["xx.dashboard.export.wizard"]
        self.Filter = self.env["xx.dyn.custom.filter"]

        # Create a dashboard with a custom filter
        self.dashboard = self.Dashboard.create(
            {
                "name": "Test Export Filter Dashboard",
                "xx_custom_filter_ids": [
                    (
                        0,
                        0,
                        {
                            "filter_name": "Test Filter",
                            "use_odoo_data": True,
                            "model_id": self.env.ref("base.model_res_country").id,
                            "model_field_name": self.env.ref(
                                "base.field_res_country__display_name"
                            ).id,
                            "model_field_value": self.env.ref("base.field_res_country__id").id,
                        },
                    )
                ],
            }
        )

        # Trigger selection computation to populate selection_ids
        self.dashboard.xx_custom_filter_ids._compute_selections()
        self.assertTrue(self.dashboard.xx_custom_filter_ids.selection_ids)

        self.export_wizard = self.Wizard.create({})

    def test_export_custom_filter_no_selections(self):
        # Call export_model_data
        xml_output = self.export_wizard.export_model_data(self.Dashboard, [self.dashboard.id])
        xml_str = str(xml_output)

        # Check that xx_custom_filter_ids is in the XML
        self.assertIn("xx_custom_filter_ids", xml_str)

        # Check that selection_ids is NOT in the XML for the custom filter
        self.assertNotIn("selection_ids", xml_str)

        # Verify it still contains other fields of the filter to be sure
        self.assertIn("filter_name", xml_str)
        self.assertIn("Test Filter", xml_str)
