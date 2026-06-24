import base64

from lxml import etree as ET

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "export_import")
class TestExportImportFull(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Wizard = self.env["xx.dashboard.export.wizard"]
        self.ExportItems = self.env["xx.export.items"]
        self.Dashboard = self.env["xx.dashboard"]

        # Create a dashboard for testing
        self.test_dashboard = self.Dashboard.create(
            {
                "name": "Test Dashboard",
                "show_date_filter": True,
            }
        )

        # Create a tile for the dashboard
        self.env["xx.dashboard.tile"].create(
            {
                "name": "Test Tile",
                "dashboard_id": self.test_dashboard.id,
                "display_type": "text",
            }
        )

    def test_onchange_export_items(self):
        wizard = self.Wizard.new(
            {
                "export_items": [
                    Command.create({"name": "Item 1", "res_id": self.test_dashboard.id})
                ],
                "filename": "test.xml",
            }
        )
        wizard._onchange_export_items()
        self.assertIn("-Test Dashboard", wizard.filename)

    def test_onchange_model_id(self):
        wizard = self.Wizard.create({})
        # Trigger onchange_model_id
        wizard.model_id = self.env["ir.model"].search([("model", "=", "xx.dashboard")], limit=1)
        wizard._onchange_model_id()

        export_items = self.env["xx.export.items"].search([("res_id", "=", self.test_dashboard.id)])
        self.assertTrue(export_items)

    def test_get_filename_suffix(self):
        wizard = self.Wizard.create(
            {"export_items": [Command.create({"name": "Item 1", "res_id": self.test_dashboard.id})]}
        )
        suffix = wizard.get_filename_suffix()
        self.assertEqual(suffix, "-Test Dashboard")

    def test_write_log(self):
        wizard = self.Wizard.create({})
        wizard.write_log("Test message")
        self.assertIn("Test message", wizard.action_log)
        wizard.write_log("Another message")
        self.assertIn("Another message", wizard.action_log)

    def test_get_xmlid_tag(self):
        wizard = self.Wizard.create({})
        xmlid = wizard.get_xmlid_tag(self.test_dashboard)
        self.assertTrue(xmlid)
        # Should start with __import__.xx_dashboard_
        self.assertTrue(xmlid.startswith("__import__.xx_dashboard_"))

        # Test with provided xmlid - it only creates/updates ir.model.data if not existing
        # But it returns the xmlid provided
        xmlid2 = wizard.get_xmlid_tag(self.test_dashboard, xmlid="test_module.test_xmlid")
        self.assertTrue(xmlid2)
        # If the record already has an XML ID (from the previous call), it might return that one?
        # Actually get_xmlid_tag logic:
        # data = self.env['ir.model.data'].search([('model', '=', obj._name),
        # ('res_id', '=', obj.id)])
        # if len(data) > 0: return data[0].module + '.' + data[0].name
        # So yes, it will return the one created above.
        self.assertTrue(xmlid2.startswith("__import__.xx_dashboard_"))

    def test_get_xmlid_tag_new(self):
        # Test with a new record that has no XML ID yet
        dashboard = self.Dashboard.create({"name": "New Dashboard"})
        wizard = self.Wizard.create({})
        xmlid = wizard.get_xmlid_tag(dashboard, xmlid="test_module.test_xmlid_new")
        self.assertEqual(xmlid, "test_module.test_xmlid_new")

    def test_export_xml(self):
        wizard = self.Wizard.create(
            {
                "name": "Export",
                "export_items": [
                    Command.create(
                        {"name": self.test_dashboard.name, "res_id": self.test_dashboard.id}
                    )
                ],
            }
        )
        result = wizard.export_xml()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertTrue(result["url"])

    def test_import_xmlfile(self):
        # First export to get some XML content
        wizard_exp = self.Wizard.create(
            {
                "export_items": [
                    Command.create(
                        {"name": self.test_dashboard.name, "res_id": self.test_dashboard.id}
                    )
                ]
            }
        )
        datas = wizard_exp.export_model_data(self.Dashboard, [self.test_dashboard.id])

        wizard_imp = self.Wizard.create(
            {"filename": "import.xml", "filecontent": base64.b64encode(datas)}
        )
        result = wizard_imp.import_xmlfile()
        self.assertEqual(result["res_id"], wizard_imp.id)
        self.assertIn("End Import", wizard_imp.action_log)

    def test_import_xml_existing_record(self):
        # Prepare XML for an existing dashboard
        xmlid = (
            self.env["ir.model.data"]
            .create(
                {
                    "model": "xx.dashboard",
                    "res_id": self.test_dashboard.id,
                    "module": "test_import",
                    "name": "existing_dashboard",
                }
            )
            .complete_name
        )

        xml_content = f"""
        <data>
            <{xmlid}>
                <name>Updated Dashboard Name</name>
            </{xmlid}>
        </data>
        """
        root = ET.fromstring(xml_content)
        wizard = self.Wizard.create({})
        wizard.import_xml(root)

        self.assertEqual(self.test_dashboard.name, "Updated Dashboard Name")

    def test_recursive_dict_special_types(self):
        wizard = self.Wizard.create({})

        # Test one2many type in XML
        root = ET.Element("data")
        o2m_field = ET.SubElement(root, "tile_ids", type="one2many")
        line = ET.SubElement(o2m_field, "tile_1")
        name = ET.SubElement(line, "name")
        name.text = "Tile Name"

        res = wizard.etree2dict(root)
        self.assertEqual(res["data"]["tile_ids"]["tile_1"]["name"], "Tile Name")

        # Test many2one type in XML
        root2 = ET.Element("data")
        m2o_field = ET.SubElement(root2, "dashboard_id", type="many2one")
        ET.SubElement(m2o_field, "test_import.existing_dashboard")

        res2 = wizard.etree2dict(root2)
        self.assertEqual(res2["data"]["dashboard_id"][0], "test_import.existing_dashboard")

    def test_prepare_data_complex(self):
        wizard = self.Wizard.create({})

        # XML ID that exists
        xmlid_existing = (
            self.env["ir.model.data"]
            .create(
                {
                    "model": "xx.dashboard",
                    "res_id": self.test_dashboard.id,
                    "module": "test_prep",
                    "name": "dashboard_1",
                }
            )
            .complete_name
        )

        data = {
            "name": "New Name",
            "tile_ids": {
                "new_tile_xmlid": {"name": "New Tile"},
                xmlid_existing: {
                    "name": "Update Existing"
                },  # This is wrong for o2m but tests logic
            },
            "parent_menu_id": ("base.menu_administration", {}),
        }

        prep_data, xids = wizard.prepare_data(data)
        # parent_menu_id should be resolved to its integer ID
        self.assertEqual(prep_data["parent_menu_id"], self.env.ref("base.menu_administration").id)
        # tile_ids should be converted to Odoo commands
        self.assertTrue(isinstance(prep_data["tile_ids"], list))

    def test_export_model_data_with_m2m(self):
        # res.groups has category_id (many2one) and implied_ids (many2many)
        # We'll use res.groups for this test
        Group = self.env["res.groups"]
        test_group = Group.create({"name": "Test Group"})
        implied_group = Group.create({"name": "Implied Group"})
        test_group.implied_ids = [Command.link(implied_group.id)]

        wizard = self.Wizard.create({})
        xml_data = wizard.export_model_data(Group, [test_group.id])
        # Currently, M2M fields are exported as strings like 'res.groups(88,)'
        self.assertIn(b"implied_ids", xml_data)
        self.assertIn(b"res.groups", xml_data)

    def test_recursive_dict_empty(self):
        wizard = self.Wizard.create({})
        # Test one2many type in XML empty
        root = ET.Element("data")
        ET.SubElement(root, "tile_ids", type="one2many")
        res = wizard.etree2dict(root)
        self.assertEqual(res["data"]["tile_ids"], {})

        # Test many2one type in XML empty
        root2 = ET.Element("data")
        ET.SubElement(root2, "dashboard_id", type="many2one")
        res2 = wizard.etree2dict(root2)
        self.assertEqual(res2["data"]["dashboard_id"], ())

    def test_getElementValue_edge_cases(self):
        wizard = self.Wizard.create({})

        # Test empty text for various types
        el_int = ET.Element("field", type="integer")
        el_int.text = ""
        # len(element.text.strip()) > 0 and int(element.text.strip()) returns False/None?
        # len("") > 0 is False. False and ... is False.
        # But it might return None if it falls through?
        # Actually it returns False because len("") > 0 is False.
        self.assertFalse(wizard.getElementValue(el_int))

        el_float = ET.Element("field", type="float")
        el_float.text = "   "
        self.assertFalse(wizard.getElementValue(el_float))

        # Test float with no type attr but has text
        el_no_type = ET.Element("field")
        el_no_type.text = "Just text"
        self.assertEqual(wizard.getElementValue(el_no_type), "Just text")

        # Test no text, no attrib
        el_empty = ET.Element("field")
        self.assertIsNone(wizard.getElementValue(el_empty))

    def test_import_xml_error_handling(self):
        # Test import_xml with a malformed tag that causes KeyError in Model lookup
        xml_content = """
        <data>
            <__import__.non_existent_model_1>
                <name>Error</name>
            </__import__.non_existent_model_1>
        </data>
        """
        root = ET.fromstring(xml_content)
        wizard = self.Wizard.create({})
        with self.assertRaises(KeyError):
            wizard.import_xml(root)

    def test_onchange_export_items_empty(self):
        wizard = self.Wizard.new({"export_items": [], "filename": "test.xml"})
        wizard._onchange_export_items()
        self.assertEqual(wizard.filename, "test.xml")

    def test_import_xmlfile_error(self):
        # Test with invalid XML content
        wizard = self.Wizard.create(
            {"filename": "invalid.xml", "filecontent": base64.b64encode(b"invalid xml")}
        )
        with self.assertRaises(ET.XMLSyntaxError):
            wizard.import_xmlfile()

    def test_recursive_dict_text_only(self):
        wizard = self.Wizard.create({})
        root = ET.Element("data")
        root.text = "Simple Text"
        tag, res = wizard.recursive_dict(root)
        self.assertEqual(res, "Simple Text")

    def test_prepare_data_o2m_no_vals(self):
        wizard = self.Wizard.create({})
        # o2m line with no values (only existing ref)
        xmlid = (
            self.env["ir.model.data"]
            .create(
                {
                    "model": "xx.dashboard.tile",
                    "res_id": self.env["xx.dashboard.tile"].search([], limit=1).id,
                    "module": "test",
                    "name": "tile_ref",
                }
            )
            .complete_name
        )

        data = {"tile_ids": {xmlid: {}}}
        prep_data, xids = wizard.prepare_data(data)
        # Should be (4, res_id)
        self.assertEqual(prep_data["tile_ids"][0][0], 4)

    def test_record_res_id_many2one_search(self):
        wizard = self.Wizard.create({})
        # Create a dashboard with a specific name and a specific menu (many2one)
        menu = self.env.ref("dyn_dashboard.menu_dyn_dashboard_overview")
        dash = self.Dashboard.create({"name": "Search Dashboard", "parent_menu_id": menu.id})

        # record_res_id(model, vals)
        vals = {"name": "Search Dashboard", "parent_menu_id": menu.id}
        res_id = wizard.record_res_id("xx.dashboard", vals)
        self.assertEqual(res_id, dash.id)

    def test_getElementValue(self):
        wizard = self.Wizard.create({})

        el_int = ET.Element("field", type="integer")
        el_int.text = " 123 "
        self.assertEqual(wizard.getElementValue(el_int), 123)

        el_float = ET.Element("field", type="float")
        el_float.text = " 123.45 "
        self.assertEqual(wizard.getElementValue(el_float), 123.45)

        el_bool = ET.Element("field", type="boolean")
        el_bool.text = " True "
        self.assertEqual(wizard.getElementValue(el_bool), True)

        el_date = ET.Element("field", type="date")
        el_date.text = " 2023-01-01 "
        # arrow.get("2023-01-01").timestamp is a method, not the value
        import arrow

        expected_ts = arrow.get("2023-01-01").timestamp()
        self.assertEqual(wizard.getElementValue(el_date), expected_ts)

        el_nil = ET.Element("field", nil="true")
        self.assertIsNone(wizard.getElementValue(el_nil))

    def test_export_dashboard_config(self):
        action = self.Wizard.export_dashboard_config()
        self.assertEqual(action["res_model"], "xx.dashboard.export.wizard")
        self.assertEqual(action["type"], "ir.actions.act_window")

    def test_import_xml_new_record(self):
        # Prepare XML for a new dashboard
        # Use a tag that matches the model name pattern expected by the bug in import_xml
        # Model = self.env[".".join(xmlid.split(".")[1].split("_")[:-1])]
        # If xmlid is __import__.xx_dashboard_1, it splits to xx_dashboard_1, then xx, dashboard.
        xml_content = """
        <data>
            <__import__.xx_dashboard_1>
                <name>New Imported Dashboard</name>
                <show_date_filter type="boolean">True</show_date_filter>
            </__import__.xx_dashboard_1>
        </data>
        """
        root = ET.fromstring(xml_content)
        wizard = self.Wizard.create({})
        dashboard_ids = wizard.import_xml(root)

        new_dashboard = self.env["xx.dashboard"].search([("name", "=", "New Imported Dashboard")])
        self.assertTrue(new_dashboard)
        self.assertIn("__import__.xx_dashboard_1", dashboard_ids)

    def test_record_res_id(self):
        wizard = self.Wizard.create({})
        res_id = wizard.record_res_id("xx.dashboard", {"name": "Test Dashboard"})
        self.assertEqual(res_id, self.test_dashboard.id)

    def test_tile_inherit_compute_query(self):
        # Set wizard status to running
        wizard = self.Wizard.create({"import_status": "running"})
        tile = self.env["xx.dashboard.tile"].search([], limit=1)
        tile._compute_query()
        self.assertEqual(wizard.import_status, "stopped")
