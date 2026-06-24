import datetime as dt
import os
import shutil
from tempfile import TemporaryDirectory

from dateutil.relativedelta import relativedelta
from lxml import etree as ET

from odoo import exceptions
from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestDynDashboard(TransactionCase):
    def setUp(self):
        super().setUp()

        self.Dashboard = self.env["xx.dashboard"]
        self.Tile = self.env["xx.dashboard.tile"]
        self.QueryKey = self.env["xx.dashboard.query.field"]
        self.Filter = self.env["xx.dyn.custom.filter"]
        self.FilterValue = self.env["xx.dyn.custom.filter.value"]
        self.Menu = self.env["ir.ui.menu"]
        self.Wizard = self.env["xx.dashboard.export.wizard"]
        self.ExportItems = self.env["xx.export.items"]
        self.Model = self.env["ir.model"]
        self.ValidationPattern = self.env["xx.dashboard.validation.patterns"]
        self.Partner = self.env["res.partner"]
        self.Activity = self.env["mail.activity"]

        self.tmpdir = TemporaryDirectory()

        # Drill dashboard needs menu_name.  Without it will not have an action,
        # which is needed to be able to drill to
        self.tile1_drill = self.Dashboard.create(
            {"name": "Drill Through Dashboard", "menu_name": "Drill DB"}
        )
        tile1_vals = {
            "name": "Tile 1",
            "display_type": "kpi",
            "drill_type": "dashboard",
            "xx_dashboard_drill": self.tile1_drill.id,
            "query": "select 100 as value;",
        }
        tile2_vals = {"name": "Tile 2", "display_type": "bar_chart"}
        filter1_vals = {
            "filter_name": "Filter 1",
            "wildcard": "_CUSTOMER_",
            "query_wildcard_replace": "customer_name = '_CUSTOMER_'",
        }

        filter2_selection_vals = {"sequence": 0, "name": "testsequence", "value": "test"}
        filter2_vals = {
            "filter_name": "Filter 2",
            "wildcard": "_SUPPLIER_",
            "query_wildcard_replace": "customer_name = '_SUPPLIER_'",
            "manual_selection_ids": [(0, 0, filter2_selection_vals)],
        }

        # Filter3 : Multiselect
        filter3_selection1_vals = {
            "sequence": 0,
            "name": "Software Developer",
            "value": "Software Developer",
        }
        filter3_selection2_vals = {"sequence": 1, "name": "Analyst", "value": "Analyst"}
        filter3_vals = {
            "filter_name": "Function",
            "wildcard": "_FUNCTION_",
            "query_wildcard_replace": "p.function = _FUNCTION_",
            "manual_selection_ids": [
                (0, 0, filter3_selection1_vals),
                (0, 0, filter3_selection2_vals),
            ],
            "multiselect": True,
        }

        # Filter 4 : Single Select
        filter4_selection1_vals = {
            "sequence": 0,
            "name": "Value_1",
            "value": "Value 1",
        }
        filter4_selection2_vals = {"sequence": 1, "name": "Value_2", "value": "Value 2"}
        filter4_vals = {
            "filter_name": "Filter 4",
            "wildcard": "_FUNCTION_",
            "query_wildcard_replace": "p.function = _FUNCTION_",
            "manual_selection_ids": [
                (0, 0, filter4_selection1_vals),
                (0, 0, filter4_selection2_vals),
            ],
            "multiselect": False,
        }

        filter5_vals = {
            "filter_name": "Filter 5",
            "use_odoo_data": True,
            "model_id": self.env.ref("base.model_res_country").id,
            "model_field_name": self.env.ref("base.field_res_country__display_name").id,
            "model_field_value": self.env.ref("base.field_res_country__id").id,
        }

        filter6_vals = {
            "filter_name": "Filter 6",
            "use_odoo_data": True,
        }

        self.dashboard = self.Dashboard.create(
            {
                "name": "Test Dashboard",
                "tile_ids": [(0, None, tile1_vals), (0, None, tile2_vals)],
                "xx_custom_filter_ids": [
                    (0, None, filter1_vals),
                    (0, None, filter2_vals),
                    (0, None, filter3_vals),
                    (0, None, filter4_vals),
                    (0, None, filter5_vals),
                    (0, None, filter6_vals),
                ],
                "menu_name": "Test Dashboard",
            }
        )

        self.export_wizard = self.Wizard.create({})

        self.dashboard_noresult = self.Dashboard.create(
            {
                "name": "Empty Dashboard",
                "tile_ids": [
                    (
                        0,
                        None,
                        {
                            "name": "No Result",
                            "query": "select 1 as one, 2 as two where 1=2",
                        },
                    )
                ],
            }
        )

    def create_xmlfile(self):
        self.xml_output = self.export_wizard.export_model_data(
            self.Dashboard, [self.dashboard.id, self.tile1_drill.id]
        )

        with open(os.path.join(self.tmpdir.name, "unittest.xml"), "wb") as f:
            f.write(self.xml_output)

    def subtitle_test(self, chart):
        subtitle = "SubTitle"
        chart["sub_title"] = subtitle
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertEqual(
            tile_data[chart.id]["options"]["title"]["text"],
            subtitle,
            "Subtitle properties set correctly",
        )

    def test_fetch_barchart(self):
        tile_data = self.Dashboard.dyn_fetch_item(
            [x.id for x in self.dashboard.tile_ids], self.dashboard.id
        )
        self.assertTrue("name" in tile_data[self.dashboard.tile_ids[0].id], "Tile data incorrect")

        # Test vertical barchart locale
        chart = self.env.ref("dyn_dashboard.xx_dashboard_tile_demo-ver-bar")
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertEqual(
            tile_data[chart.id]["locale"], "nl-BE", "Default graph locale is incorrect"
        )
        # --- Update locale
        chart.write({"graph_locale": "en-US"})
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertEqual(
            tile_data[chart.id]["locale"], "en-US", "Default graph locale is incorrect"
        )

        # Test radial barchart locale
        chart = self.env.ref("dyn_dashboard.xx_dashboard_tile_radialbarchart")
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertEqual(
            tile_data[chart.id]["locale"],
            "en-US",
            "Dashboard locale not overwritten by graph locale",
        )
        # Test semicircle radial barchart properties
        chart["is_radial_semi_circle"] = True
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertEqual(
            tile_data[chart.id]["options"]["plotOptions"]["radialBar"]["startAngle"],
            -90,
            "Semi circle properties not set",
        )

        # Test semicircle radial barchart show labels
        chart["show_labels"] = True
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertTrue(
            tile_data[chart.id]["options"]["plotOptions"]["radialBar"]["dataLabels"]["name"][
                "show"
            ],
            "Show Labels properties not set",
        )
        # Test radial barchart subtitle
        self.subtitle_test(chart)

    def test_linechart(self):
        # Test linechart locale
        chart = self.env.ref("dyn_dashboard.xx_dashboard_tile_linechart")
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertEqual(
            tile_data[chart.id]["locale"], "nl-BE", "Default linechart locale is incorrect"
        )
        self.subtitle_test(chart)

    def test_piechart(self):
        # Test piechart locale
        chart = self.env.ref("dyn_dashboard.xx_dashboard_tile_piechart")
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        self.assertEqual(
            tile_data[chart.id]["locale"], "nl-BE", "Default piechart locale is incorrect"
        )
        self.subtitle_test(chart)

    def test_fetch_dummy_tile(self):
        # Test fetch dummy tile data
        item = self.env.ref("dyn_dashboard.xx_dashboard_tile_dummy")
        tile_data = self.Dashboard.dyn_fetch_item([item.id], item.dashboard_id)
        self.assertTrue(tile_data, "no dummy tile data returned")

    def test_fetch_table_tile(self):
        # Test fetch table tile data
        item = self.env.ref("dyn_dashboard.xx_dashboard_tile_table")
        tile_data = self.Dashboard.dyn_fetch_item([item.id], item.dashboard_id)
        self.assertTrue(tile_data, "no table tile data returned")

    def test_fetch_text_tile(self):
        # Test fetch text tile data
        item = self.Tile.create(
            {
                "name": "Text Tile",
                "dashboard_id": self.dashboard.id,
                "display_type": "text",
                "plain_text": "test",
            }
        )
        tile_data = self.Dashboard.dyn_fetch_item([item.id], item.dashboard_id)
        self.assertTrue(tile_data, "no table tile data returned")

    def test_stacked_linechart(self):
        # Test stacked linechart properties
        chart = self.env.ref("dyn_dashboard.xx_dashboard_tile_linechart-column")
        chart["is_stacked"] = True
        tile_data = self.Dashboard.dyn_fetch_item([chart.id], chart.dashboard_id.id)
        sum_chart_values = (
            max([max(x["data"]) for x in tile_data[chart.id]["options"]["series"]]) * 1.1
        )
        self.assertEqual(
            tile_data[chart.id]["options"]["yaxis"]["max"],
            sum_chart_values,
            "Stacked Linechart has incorrect Y-axis size (max)",
        )

    def test_export_wizard(self):
        """Test select of items to export in the wizard"""
        wizard = self.Wizard.create({"name": "Test Wizard"})
        with Form(wizard) as wf:
            self.assertEqual(
                wf.model_id,
                self.env.ref("dyn_dashboard.model_xx_dashboard"),
                "Wizard model incorrect",
            )
            wf.export_items.add(
                self.ExportItems.search(
                    [("wizard_id", "=", wizard.id), ("name", "=", self.dashboard.name)]
                )
            )

    def test_dashboard_create(self):
        self.assertEqual(self.dashboard.name, "Test Dashboard")
        self.assertTrue(self.Menu.search([("name", "=", "Test Dashboard")]), "Menu was not created")

    def test_dashboard_delete(self):
        dashboard_id = self.dashboard.id
        tile_ids = self.Tile.search([("dashboard_id", "=", dashboard_id)])
        query_key_ids = [x.query_key_ids.id for x in tile_ids if x.query_key_ids]
        self.dashboard.unlink()

        # test dashboard tiles are deleted
        self.assertFalse(
            self.Tile.search([("dashboard_id", "=", dashboard_id)]), "Tiles were not deleted"
        )

        # test query fields are deleted
        self.assertFalse(
            self.QueryKey.search([("id", "in", query_key_ids)]), "Fields were not deleted"
        )

        # test filters are deleted
        self.assertFalse(
            self.Filter.search([("dashboard_id", "=", dashboard_id)]), "Filters were not deleted"
        )

        # test menus are deleted
        self.assertFalse(
            self.Menu.search([("name", "=", "Test Dashboard")]), "Menu was not deleted"
        )

    def test_datefilter_fetch_dashboard_data(self):
        dashboard_data = self.dashboard.with_context(
            **{"dynDateFilterSelection": "l_day"}
        ).fetch_dashboard_data(self.dashboard.id)
        self.assertEqual(
            (dashboard_data["dashboard_end_date"] - dashboard_data["dashboard_start_date"]),
            dt.timedelta(days=0, hours=23, minutes=59, seconds=59),
            "incorrect duration for l_<period>",
        )

        dashboard_data = self.dashboard.with_context(
            **{"dynDateFilterSelection": "n_week"}
        ).fetch_dashboard_data(self.dashboard.id)
        self.assertEqual(
            (dashboard_data["dashboard_end_date"] - dashboard_data["dashboard_start_date"]),
            dt.timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=59000),
            "incorrect duration for n_<period>",
        )
        today = dt.datetime.now()
        dashboard_data = self.dashboard.with_context(
            **{"dynDateFilterSelection": "ls_month"}
        ).fetch_dashboard_data(self.dashboard.id)
        self.assertEqual(
            (dashboard_data["dashboard_end_date"] - dashboard_data["dashboard_start_date"]),
            (dt.datetime(today.year, today.month, 1) - dt.timedelta(seconds=1))
            - dt.datetime(
                (today - relativedelta(months=1)).year, (today - relativedelta(months=1)).month, 1
            ),
            "incorrect duration for ls_<period>",
        )

        dashboard_data = self.dashboard.with_context(
            **{"dynDateFilterSelection": "t_year"}
        ).fetch_dashboard_data(self.dashboard.id)
        self.assertEqual(
            (dashboard_data["dashboard_end_date"] - dashboard_data["dashboard_start_date"]),
            dt.datetime(today.year + 1, 1, 1)
            - dt.datetime(today.year, 1, 1)
            - dt.timedelta(seconds=1),
            "incorrect duration for t_<period>",
        )

        start_quarter = dt.datetime(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
        end_quarter = start_quarter + relativedelta(months=3, seconds=-1)
        self.env.user.tz = "UTC"
        dashboard_data = self.dashboard.with_context(
            **{"dynDateFilterSelection": "t_quarter"}
        ).fetch_dashboard_data(self.dashboard.id)
        self.assertEqual(
            dashboard_data["dashboard_start_date"],
            start_quarter,
            "incorrect start date for t_quarter",
        )
        self.assertEqual(
            dashboard_data["dashboard_end_date"], end_quarter, "incorrect end date for t_quarter"
        )

    def test_fetch_dashboard_data_orig_id(self):
        # Test if filter set in initial dashboard is returned when fetching drill-through dashboard
        filter_id = self.env.ref(
            "dyn_dashboard.xx_dyn_custom_filter_selection_company"
        ).filter_id.id
        filter_name = self.env.ref(
            "dyn_dashboard.xx_dyn_custom_filter_selection_company"
        ).filter_id.filter_name
        filter_value = True
        context = {"dynCustomFilters": [{"filter_id": filter_id, "value": filter_value}]}
        self.FilterValue.with_context(**context).update_values(filter_id)
        dashboard_data = self.dashboard.with_context(
            **{"dashboard_id_orig": self.env.ref("dyn_dashboard.xx_dashboard_demo").id}
        ).fetch_dashboard_data(self.env.ref("dyn_dashboard.xx_dashboard_drill").id)
        custom_filter_values = [
            x for x in dashboard_data["custom_filters"] if x["name"] == filter_name
        ]
        self.assertTrue(custom_filter_values)
        self.assertEqual(
            custom_filter_values[0]["value"],
            str(filter_value),
            "invalid filter value on drill through",
        )
        self.assertEqual(
            custom_filter_values[0]["name"], filter_name, "invalid filter value on drill through"
        )

        filter_value = False
        context = {"dynCustomFilters": [{"filter_id": filter_id, "value": filter_value}]}
        self.FilterValue.with_context(**context).update_values(filter_id)
        dashboard_data = self.dashboard.with_context(
            **{"dashboard_id_orig": self.env.ref("dyn_dashboard.xx_dashboard_demo").id}
        ).fetch_dashboard_data(self.env.ref("dyn_dashboard.xx_dashboard_drill").id)
        custom_filter_values = [
            x for x in dashboard_data["custom_filters"] if x["name"] == filter_name
        ]
        self.assertTrue(custom_filter_values)

    def test_tile_create(self):
        tile1 = self.Tile.search([("name", "=", "Tile 1")])
        tile2 = self.Tile.search([("name", "=", "Tile 2")])
        self.assertEqual(tile1["display_type"], "kpi", "Tile not created correctly")
        self.assertEqual(tile2["display_type"], "bar_chart", "Tile not created correctly")

    def test_export_xml(self):
        self.create_xmlfile()
        self.assertIn(
            self.dashboard.name, str(self.xml_output), "XML output does not contain Dashboard data"
        )
        self.assertNotIn("<__import__..xx_dashboard_", str(self.xml_output), "XML ID incorrect")
        self.assertIn("Tile 1", str(self.xml_output), "XML output does not contain Tile1 data")
        self.assertIn("Tile 2", str(self.xml_output), "XML output does not contain Tile2 data")
        self.assertIn("Filter 1", str(self.xml_output), "XML output does not contain Filter1 data")
        self.assertIn("Filter 2", str(self.xml_output), "XML output does not contain Filter2 data")
        self.assertIn("create_date", str(self.xml_output), "XML output contains create date")
        self.assertIn("write_date", str(self.xml_output), "XML output contains write date")
        # Test date field does not contain boolean values
        self.assertNotIn(
            "<dashboard_start_date>False</dashboard_start_date>",
            str(self.xml_output),
            "XML output contains write date",
        )
        # Test o2m field does not contain value
        self.assertNotIn(
            '<xx_custom_filter_ids type="one2many">l_none</xx_custom_filter_ids>',
            str(self.xml_output),
            "XML output contains write date",
        )
        # Test m2o field does not contain value
        self.assertNotIn(
            '<model_id type="many2one">bar_chart</model_id>',
            str(self.xml_output),
            "XML output contains write date",
        )
        self.assertIn(
            "Drill Through Dashboard",
            str(self.xml_output),
            "XML output does not contain drill through dashboard",
        )

        # Test if Base model reference fields are only exported by their xmlid so they are not
        # created when imported in another environment
        self.assertIn(
            '<model_id type="many2one"><base.model_res_country/></model_id>',
            str(self.xml_output),
            "Filter 5 Odoo Model not found in xml",
        )

        self.assertIn(
            '<model_field_name type="many2one"><base.field_res_country__display_name'
            "/></model_field_name>",
            str(self.xml_output),
            "Filter 5 Odoo Field Name not found in xml",
        )

        self.assertIn(
            '<model_field_value type="many2one"><base.field_res_country__id/></model_field_value>',
            str(self.xml_output),
            "Filter 5 Odoo Field Value not found in xml",
        )

    def test_import_xml(self):
        self.create_xmlfile()
        self.dashboard.unlink()  # delete dashboard before import
        xml_filename = os.path.join(self.tmpdir.name, "unittest.xml")
        etree = ET.parse(xml_filename)
        dashboard_ids = self.Wizard.import_xml(etree.getroot())
        self.assertGreaterEqual(len(dashboard_ids), 0, "Dashboard not created")
        xmlids = list(dashboard_ids.keys())
        dashboard0 = dashboard_ids[xmlids[0]]
        self.assertEqual(
            dashboard0.name, "Drill Through Dashboard", "Dashboard not imported correctly"
        )
        dashboard1 = dashboard_ids[xmlids[1]]
        self.assertEqual(dashboard1.name, "Test Dashboard", "Dashboard not imported correctly")

        self.assertEqual(len(dashboard1.tile_ids), 2, "Dashboard not imported correctly")

        self.assertRecordValues(
            dashboard1,
            [
                {
                    "date_filter_selection": "l_none",
                }
            ],
        )
        # Test if drill-through dashboard gets linked if it exists
        self.assertRecordValues(
            dashboard1.tile_ids[0].xx_dashboard_drill, [{"name": "Drill Through Dashboard"}]
        )
        # Test if the custom filters are imported with underlying selections
        self.assertRecordValues(
            dashboard1.xx_custom_filter_ids[1],
            [{"filter_name": "Filter 2", "wildcard": "_SUPPLIER_"}],
        )

        self.assertRecordValues(
            dashboard1.xx_custom_filter_ids[1].manual_selection_ids,
            [{"name": "testsequence", "value": "test"}],
        )

    def test_empty_query(self):
        # Test dashboard with empty query
        self.dashboard_empty = self.Dashboard.create(
            {
                "name": "Empty Dashboard",
                "tile_ids": [
                    (
                        0,
                        None,
                        {
                            "name": "No Query",
                            "query": False,
                            "query_key_ids": [(0, None, {"sequence": 0, "name": "Zero"})],
                        },
                    )
                ],
            }
        )
        self.assertTrue(self.dashboard_empty)
        query_field = self.QueryKey.search([("name", "=", "Zero")])
        self.assertTrue(query_field)

    def test_noresult_query(self):
        # Test dashboard with query returning no result
        self.assertTrue(self.dashboard_noresult)
        query_field = self.dashboard_noresult.tile_ids[0].query_key_ids[0]
        self.assertEqual(
            query_field.field_label, query_field.name.title(), "Field Label not in initial case"
        )

    def test_odoo_data_filter(self):
        # Test filter(_5) with use_odoo_data and model_id contains selection_ids
        filter5 = self.Filter.search([("filter_name", "=", "Filter 5")])
        filter5._compute_selections()
        self.assertTrue(filter5.selection_ids, "No selection_ids for filter using Odoo data")

        # Test filter(_6) with use_odoo_data but no model_id does not contain selection_ids
        filter6 = self.Filter.search([("filter_name", "=", "Filter 6")])
        filter6._compute_selections()
        self.assertFalse(filter6.selection_ids, "Selection_ids found in filter without model_id")

    def test_multiselect_filter_values(self):
        # Test if stored multiselect filter values get retreived correctly
        filter_values = ["Software Developer", "Analyst"]
        dashboard_id = self.dashboard.id
        dashboard_data = self.dashboard.fetch_dashboard_data(dashboard_id)
        custom_filter = [x for x in dashboard_data["custom_filters"] if x["name"] == "Function"][0]
        context_to_pass = {
            "dynCustomFilters": [{"filter_id": custom_filter["filter_id"], "value": filter_values}]
        }
        self.FilterValue.with_context(**context_to_pass).update_values([])

        dashboard_data = self.dashboard.fetch_dashboard_data(dashboard_id)
        custom_filter = [x for x in dashboard_data["custom_filters"] if x["name"] == "Function"][0]
        filter_value = custom_filter["value"]
        self.assertEqual(filter_value, filter_values, "Incorrect Filter values returned")

    def test_singleselect_filter_values(self):
        # Test if stored single select filter values get retreived correctly
        filter_name = "Filter 4"
        filter_values = "Value 1"
        dashboard_id = self.dashboard.id
        dashboard_data = self.dashboard.fetch_dashboard_data(dashboard_id)
        custom_filter = [x for x in dashboard_data["custom_filters"] if x["name"] == filter_name][0]
        context_to_pass = {
            "dynCustomFilters": [{"filter_id": custom_filter["filter_id"], "value": filter_values}]
        }
        self.FilterValue.with_context(**context_to_pass).update_values([])

        dashboard_data = self.dashboard.fetch_dashboard_data(dashboard_id)
        custom_filter = [x for x in dashboard_data["custom_filters"] if x["name"] == filter_name][0]
        filter_value = custom_filter["value"]
        self.assertEqual(filter_value, filter_values, "Incorrect Filter values returned")

    @mute_logger("odoo.sql_db")
    def test_large_odoodatafilter(self):
        """
        Test to check if Odoo data filter with large select list is created.
        Since this process writes to database the result is not in scope of the ut.
        """
        i = 1
        while len(self.Partner.search([])) < 1000:
            self.Partner.create({"name": "Partner " + str(i)})
            i += 1
        vals = {
            "filter_name": "Large Filter",
            "use_odoo_data": True,
            "model_id": self.env.ref("base.model_res_partner").id,
            "model_field_name": self.env.ref("base.field_res_partner__name").id,
            "model_field_value": self.env.ref("base.field_res_partner__id").id,
            "query_threshold": 999,
        }
        dashboard = self.Dashboard.create(
            {
                "name": "Test Dashboard",
                "xx_custom_filter_ids": [
                    (0, None, vals),
                ],
                "menu_name": "Test Dashboard",
            }
        )
        data = dashboard.fetch_dashboard_data(dashboard.id)
        self.assertTrue(data["custom_filters"])

    @mute_logger("odoo.sql_db")
    def test_large_odoodatafilter_usererror(self):
        """
        Test to check if Odoo data filter with large select list is created.
        Since this process writes to database the result is not in scope of the ut.
        """
        i = 1
        while len(self.Partner.search([])) < 1000:
            self.Partner.create({"name": "Partner " + str(i)})
            i += 1
        # email formatted is a computed field, so this should throw a UserError as the sql
        # query of customer filter - _compute_selections will throw an sql error (field not found)
        filter_name = "Large Filter"
        vals = {
            "filter_name": filter_name,
            "use_odoo_data": True,
            "model_id": self.env.ref("base.model_res_partner").id,
            "model_field_name": self.env.ref("base.field_res_partner__email_formatted").id,
            "model_field_value": self.env.ref("base.field_res_partner__id").id,
            "query_threshold": 99,
        }

        dashboard = self.Dashboard.with_context(no_recompute=True).create(
            {
                "name": "Test Dashboard",
                "xx_custom_filter_ids": [
                    (0, None, vals),
                ],
                "menu_name": "Test Dashboard",
            }
        )
        with self.assertRaisesRegex(
            exceptions.UserError,
            "Unable to use it in large selection list filters",
        ):
            dashboard.xx_custom_filter_ids.with_context(no_recompute=False)._compute_selections()

    def test_row_data_drill_action(self):
        """test drill dashboard with menu action returns an action"""
        tile_1 = self.dashboard.tile_ids.filtered(lambda tile: tile.name == "Tile 1")
        tile_1.xx_dashboard_drill.menu_name = "Drill Dashboard"

        data = tile_1.get_row_data_drill_action(False)
        self.assertTrue(data, "Drill action incorrect")

        data = tile_1.get_row_data_drill_action(1)
        self.assertTrue(data, "Drill action(rowid) incorrect")

    def test_validation_pattern(self):
        with Form(self.ValidationPattern) as f:
            f.validation_rule = "BH####@@@@&&&&&&&&&&&&&&"

    def test_search_selection_values(self):
        """search select list values"""
        filter5 = self.dashboard.xx_custom_filter_ids.search([("filter_name", "=", "Filter 5")])
        filter5._compute_selections()
        res = filter5.get_selection_values(str(self.env.ref("base.be").id))
        self.assertEqual(res["text"], self.env.ref("base.be").name, "Selection value not found")

        res = filter5.get_selection_values("0")
        self.assertFalse(res, "Wrong response searching non-existing selection")

    def test_rolling_selectlist(self):
        filter_5 = self.Filter.search([("filter_name", "=", "Filter 5")])
        filter_model = self.env[filter_5.model_id.model]
        query = "bel"
        filter_size = len(
            filter_model.search([]).filtered(lambda x: query.upper() in x.name.upper())
        )
        page_size = 20
        filter_5._compute_selections()

        # in case no query given: number of records equal to pagesize is returned
        select_list = filter_5.get_filter_selections(1, False)
        self.assertEqual(
            len(select_list["results"]), page_size, "Rolling select list has the wrong size"
        )

        # in case no query given: number of records corresponding query is returned
        select_list = filter_5.get_filter_selections(1, query)
        self.assertEqual(
            len(select_list["results"]), filter_size, "Rolling select list has the wrong size"
        )

    def test_table_drill(self):
        item = self.Tile.create(
            {
                "name": "Dates Table",
                "dashboard_id": self.dashboard.id,
                "display_type": "table",
                "query": "select 1 as id, 'test' as name",
                "drill_type": "filter",
            }
        )
        data = item.get_row_data_drill_action(1)
        self.assertEqual(data["drill_type"], "filter", "Wrong drill type found")
        dashboard_drill = self.Dashboard.create({"name": "Dashboard Drill", "menu_name": "Drill"})
        tile1 = self.Tile.create(
            {
                "name": "Dashboard Drill Tile",
                "display_type": "kpi",
                "drill_type": "dashboard",
                "xx_dashboard_drill": dashboard_drill.id,
                "query": "select 100 as value;",
            }
        )
        data = tile1.get_row_data_drill_action(1)
        self.assertEqual(data["drill_type"], "dashboard", "Wrong drill type found")

        tile2 = self.Tile.create(
            {
                "name": "Model Drill Tile",
                "display_type": "kpi",
                "drill_type": "model",
                "model_id": self.env.ref("base.model_res_country").id,
                "query": "select 100 as value;",
            }
        )
        data = tile2.get_row_data_drill_action(1)
        self.assertEqual(data["drill_type"], "model", "Wrong drill type found")

    def test_table_drill_with_model(self):
        """test if a table with model in de result returns the record from this model"""

        res_id = self.Partner.create({"name": "Activity Partner"})
        res_model = res_id._name
        res_model_id = self.env["ir.model"]._get(res_model).id

        activity = self.Activity.create(
            {
                "summary": "dashboard test activity",
                "res_id": res_id,
                "res_model": res_model,
                "res_model_id": res_model_id,
            }
        )
        tile = self.Tile.create(
            {
                "name": "Dashboard Drill Tile",
                "display_type": "table",
                "drill_type": "model",
                # "xx_dashboard_drill": dashboard_drill.id,
                "query": """
                    select res_id as id, res_model
                    from mail_activity
                    where summary = 'dashboard test activity';
                """,
            }
        )
        table_record = tile.get_data()["tabledata"][0]
        data = tile.get_row_data_drill_action(table_record["id"], table_record["res_model"])
        self.assertEqual(data["model_model"], activity.res_model, "Wrong model in drill data")
        self.assertEqual(data["target_id"], activity.res_id, "Wrong target in drill data")

    # TODO add tests for all table drill types

    def test_export_field_properties(self):
        field_name = "textfield"
        field_format = "money"
        tile = self.Tile.create(
            {
                "name": "Export Tile Fields",
                "query": "select 'Field Text' as " + field_name,
            }
        )
        tile.query_key_ids[0].formatter = field_format
        dashboard = self.Dashboard.create(
            {
                "name": "Empty Dashboard",
                "tile_ids": [(4, tile.id)],
            }
        )
        xml = self.Wizard.export_model_data(self.Dashboard, [dashboard.id])
        dashboard.unlink()
        self.assertFalse(
            self.QueryKey.search([("name", "=", field_name)]),
            "Dashboard delete did not delete field",
        )
        self.Wizard.import_xml(ET.fromstring(xml))
        import_field = self.QueryKey.search([("name", "=", field_name)])
        self.assertEqual(
            import_field.formatter, field_format, "Imported field has incorrect formatter"
        )

    def test_multi_create(self):
        dashboards = self.Dashboard.create(
            [
                {"name": "Dashboard 1/2", "menu_name": "First Dashboard"},
                {"name": "Dashboard 2/2", "menu_name": "Second Dashboard"},
            ]
        )
        self.assertEqual(dashboards[0].menu_id.name, dashboards[0].menu_name)
        self.assertEqual(dashboards[1].menu_id.name, dashboards[1].menu_name)

    def test_get_drill_filter_(self):
        tile_vals = {
            "name": "Tile 1",
            "display_type": "kpi",
            "drill_type": "filter",
            "xx_dashboard_drill": self.tile1_drill.id,
            "query": "select 100 as value, '1' as ids;",
        }
        testtile = self.Tile.create(tile_vals)
        data = testtile.get_data()
        self.assertEqual(data["value"], 100, "Incorrect kpi value")
        self.assertEqual(data["drill_ids"], [1], "Incorrect drill_id")

    def test_table_column_data(self):
        tile_vals = {
            "name": "Table",
            "display_type": "table",
            "query": "select 100 as value, 1 as id;",
        }
        testtile = self.Tile.create(tile_vals)
        data = testtile.get_data()
        self.assertEqual(
            list(data["columns"][0].keys()),
            ["title", "field", "hozAlign", "visible", "download", "headerFilter"],
            "Incorrect column properties",
        )

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.tmpdir.name)
