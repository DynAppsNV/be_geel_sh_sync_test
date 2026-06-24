import json

from odoo.tests.common import HttpCase


class TestController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["xx.dashboard"].create(
            {
                "name": "Test Dashboard",
            }
        )
        cls.tile = cls.env["xx.dashboard.tile"].create(
            {
                "name": "Test Tile",
                "dashboard_id": cls.dashboard.id,
                "query": "SELECT 1 as id, 'test' as name",
            }
        )
        cls.custom_filter = cls.env["xx.dyn.custom.filter"].create(
            {
                "filter_name": "Test Filter",
                "dashboard_id": cls.dashboard.id,
                "model_id": cls.env.ref("base.model_res_partner").id,
            }
        )

    def test_get_dashboard_data(self):
        """It should return dashboard data."""
        self.authenticate("admin", "admin")
        params = {
            "dashboard_id": self.dashboard.id,
            "context_to_pass": {},
        }
        response = self.url_open(
            "/dyn_dashboard/get_dashboard_data",
            data=json.dumps({"params": params}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        result = response.json().get("result")
        self.assertTrue(result)

    def test_get_tile_data(self):
        """It should return tile data."""
        self.authenticate("admin", "admin")
        params = {
            "tile_id": self.tile.id,
            "ctx": {},
        }
        response = self.url_open(
            "/dyn_dashboard/get_tile_data",
            data=json.dumps({"params": params}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        result = response.json().get("result")
        self.assertTrue(result)

    def test_get_table_drill_data(self):
        """It should return table drill data."""
        self.authenticate("admin", "admin")
        params = {
            "tile_id": self.tile.id,
            "row_id": 1,
            "res_model": "res.partner",
            "ctx": {},
        }
        response = self.url_open(
            "/dyn_dashboard/get_table_drill_data",
            data=json.dumps({"params": params}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        # result might be empty if no drill action is defined, but it should still be 200
        self.assertIn("result", response.json())

    def test_get_filter_data(self):
        """It should return filter data."""
        # This one is auth="public" and type="http"
        # BUT it still needs access to the record.
        # Since we're in an HttpCase, we should authenticate to have access to xx.dyn.custom.filter
        # if the ACLs don't allow public access.
        self.authenticate("admin", "admin")
        params = {
            "q": "",
            "page": 1,
            "filter_id": self.custom_filter.id,
            "context_to_pass": json.dumps({}),
        }
        # Using GET to avoid CSRF issues in test
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        response = self.url_open(
            f"/dyn_dashboard/get_filter_data?{query_string}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())

    def test_get_init_selection(self):
        """It should return initial selection data."""
        self.authenticate("admin", "admin")
        params = {
            "filter_id": self.custom_filter.id,
            "search_value": "",
            "context_to_pass": json.dumps({}),
        }
        response = self.url_open(
            "/dyn_dashboard/get_init_selection",
            data=json.dumps({"params": params}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.json())
