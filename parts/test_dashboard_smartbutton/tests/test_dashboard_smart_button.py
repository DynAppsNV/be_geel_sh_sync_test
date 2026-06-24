from lxml import etree

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestDynDashboardSmartButton(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Dashboard = self.env["xx.dashboard"]
        self.DashboardTile = self.env["xx.dashboard.tile"]
        model_id = self.env["ir.model"].search([("model", "=", "res.partner")]).id
        self.Dashboard.create(
            {
                "name": "test dashboard name splitting",
                "model_ids": [Command.link(model_id)],
                "icon": "fa-table",
            }
        )
        self.test_partner = self.env["res.partner"].create({"name": "Dummy Contact"})

    def test_get_dashboard_smart_button(self):
        # Case 1: Icon set, long name
        result = self.test_partner._get_dashboard_smart_button()
        self.assertEqual(
            result[0].attrib["name"], "button_open_dashboard", "Smart button not created correctly"
        )
        self.assertEqual(result[0].attrib["icon"], "fa-table")
        stat_text = result[0].xpath("//span[@class='o_stat_text']/text()")
        # dashboard name no longer gets splitted to fit the button
        self.assertEqual(stat_text, ["test dashboard name splitting"])

        # Case 2: No icon, default should be used
        model_id = self.env["ir.model"].search([("model", "=", "res.partner")]).id
        self.Dashboard.create(
            {"name": "No Icon", "model_ids": [Command.link(model_id)], "icon": False}
        )
        result = self.test_partner._get_dashboard_smart_button()
        # Find the one with "No Icon" name
        # Actually it's simpler to just check if any button has fa-line-chart
        self.assertTrue(any(b.attrib["icon"] == "fa-line-chart" for b in result))

    def test_button_open_dashboard(self):
        action = self.test_partner.button_open_dashboard()
        self.assertEqual(
            action["domain"],
            [("odoo_record_id", "=", self.test_partner.id)],
            "Incorrect domain opening button action",
        )

    def test_get_view(self):
        model = self.env["res.partner"]
        view_id = self.env.ref("base.view_partner_form").id
        arch, view = model._get_view(view_id=view_id)

        # Use XPath to find the button with the specific attributes
        button = arch.xpath(
            "//button[@class='oe_stat_button' and @icon='fa-table' and "
            "@name='button_open_dashboard']"
        )
        self.assertTrue(
            len(button) > 0,
            "Smart button not in Form view",
        )

    def test_get_view_no_button_box(self):
        model = self.env["res.partner"]
        test_view = self.env["ir.ui.view"].create(
            {
                "name": "test.partner.form.no.button.box",
                "model": "res.partner",
                "inherit_id": self.env.ref("base.view_partner_form").id,
                "arch": """
                <xpath expr="//div[@name='button_box']" position="replace"/>
            """,
            }
        )

        arch, view = model._get_view(view_id=test_view.id, view_type="form")

        # Use XPath to find the button with the specific attributes
        button = arch.xpath(
            "//button[@class='oe_stat_button' and @icon='fa-table' and "
            "@name='button_open_dashboard']"
        )
        self.assertTrue(
            len(button) > 0,
            "Smart button not in Form view",
        )

    def test_get_default_view(self):
        model = self.env["res.partner"]

        custom_arch_str = "<form><sheet><field name='name'/></sheet></form>"
        custom_arch = etree.fromstring(custom_arch_str)

        from unittest.mock import MagicMock, patch

        mock_view = MagicMock()
        mock_view.type = "form"

        # In Odoo 19 the model class must be retrieved from the registry
        IrUiView = self.env["ir.ui.view"].__class__

        with patch.object(IrUiView, "_get_view", return_value=(custom_arch, mock_view)):
            arch, view = model._get_view(view_type="form")

            # Now test the button_box logic
            button_box = arch.xpath("//div[@name='button_box']")
            self.assertTrue(button_box, "button_box should have been created")
            self.assertEqual(button_box[0].get("class"), "oe_button_box")

            sheet = arch.find("sheet")
            self.assertEqual(sheet[0].get("name"), "button_box")

    def test_replace_record_id(self):
        record_wildcard = "id=%RECORDID"
        odoo_record_id = 5
        tile = self.DashboardTile.create(
            {"name": "Test Query Replace Record ID", "odoo_record_wildcard": record_wildcard}
        )
        query = "select id from res_partner where id=%RECORDID"
        test_result = tile.with_context(odoo_record_id=odoo_record_id).replace_record_id(query)
        self.assertEqual(test_result, query.replace("%RECORDID", str(odoo_record_id)))

        test_result = tile.replace_record_id(query)
        self.assertEqual(test_result, query.replace(record_wildcard, "1=1"))
