from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestExportImport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Wizard = self.env["xx.dashboard.export.wizard"]
        self.ExportItems = self.env["xx.export.items"]

    def test_export_xml(self):
        dashboard = self.env.ref("dyn_dashboard.xx_dashboard_demo")
        # test without export items selected
        export_wizard = self.Wizard.create({})
        export_xml = export_wizard.export_xml()
        self.assertIsNone(export_xml.get("url"), "Download url returned from export xml")
        self.assertEqual(
            export_xml.get("type"),
            "ir.actions.act_window",
            "Export Xml Action not of type act_window",
        )

        # test with export items selected
        export_wizard = self.Wizard.create(
            {"export_items": [Command.create({"name": dashboard.name, "res_id": dashboard.id})]}
        )
        export_xml = export_wizard.export_xml()
        self.assertTrue(export_xml["url"], "No download url returned from export xml")
        self.assertEqual(
            export_xml.get("type"), "ir.actions.act_url", "Export Xml Action not of type url"
        )

    def test_export_dashboard_config(self):
        export_dashboard_config = self.Wizard.export_dashboard_config()
        self.assertTrue(export_dashboard_config)
