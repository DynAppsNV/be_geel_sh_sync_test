from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestResUsers(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.user

    def test_fetch_initial_dyn_dashboard_date_range(self):
        res = self.user.fetch_initial_dyn_dashboard_date_range()
        self.assertIn("initial_values", res)
        self.assertIn("fields", res)
        self.assertIn("xx_dyn_dashboard_last_selected_start_date", res["initial_values"])
        self.assertIn("xx_dyn_dashboard_last_selected_end_date", res["initial_values"])
        self.assertIn("xx_dyn_dashboard_last_selected_start_date", res["fields"])
        self.assertIn("xx_dyn_dashboard_last_selected_end_date", res["fields"])

    def test_get_user_value(self):
        # Case 1: Value is in the future
        future_date = fields.Date.today() + relativedelta(days=5)
        self.user.xx_dyn_dashboard_last_selected_start_date = future_date
        val = self.user._get_user_value("xx_dyn_dashboard_last_selected_start_date", self.user)
        self.assertEqual(val["xx_dyn_dashboard_last_selected_start_date"], future_date)

        # Case 2: Value is in the past
        past_date = fields.Date.today() - relativedelta(days=5)
        self.user.xx_dyn_dashboard_last_selected_start_date = past_date
        val = self.user._get_user_value("xx_dyn_dashboard_last_selected_start_date", self.user)
        expected_date = fields.Date.today() + relativedelta(months=1)
        self.assertEqual(val["xx_dyn_dashboard_last_selected_start_date"], expected_date)
        self.assertEqual(self.user.xx_dyn_dashboard_last_selected_start_date, expected_date)

        # Case 4: Value is today
        today = fields.Date.today()
        self.user.xx_dyn_dashboard_last_selected_start_date = today
        val = self.user._get_user_value("xx_dyn_dashboard_last_selected_start_date", self.user)
        self.assertEqual(val["xx_dyn_dashboard_last_selected_start_date"], today)

    def test_get_user_timezone_offset(self):
        self.user.tz = "Europe/Brussels"  # UTC+1 (Winter) or UTC+2 (Summer)
        offset = self.user.get_user_timezone_offset()
        self.assertIsInstance(offset, timedelta)

        self.user.tz = "America/New_York"
        offset_ny = self.user.get_user_timezone_offset()
        self.assertIsInstance(offset_ny, timedelta)

        self.user.tz = False  # Should default to GMT
        offset_gmt = self.user.get_user_timezone_offset()
        self.assertEqual(offset_gmt, timedelta(0))

    def test_adjust_datetime(self):
        self.user.tz = "UTC"
        dt_str = "2024-01-01T12:00:00.000Z"
        dt_obj = datetime(2024, 1, 1, 12, 0, 0)

        # Test string input
        adj = self.user.adjust_datetime(dt_str)
        self.assertEqual(adj, dt_obj)

        # Test datetime input
        adj = self.user.adjust_datetime(dt_obj)
        self.assertEqual(adj, dt_obj)

        # Test subtract=False
        adj = self.user.adjust_datetime(dt_obj, subtract=False)
        self.assertEqual(adj, dt_obj)

        # Test invalid input
        self.assertFalse(self.user.adjust_datetime(None))

        # Test timezone offset adjustment
        self.user.tz = "America/New_York"  # UTC-5
        # Since it's winter (Jan 1), it's -5h
        adj = self.user.adjust_datetime(dt_obj, subtract=True)
        # 12:00 - (-5h) = 17:00
        self.assertEqual(adj.hour, 17)

        adj = self.user.adjust_datetime(dt_obj, subtract=False)
        # 12:00 + (-5h) = 07:00
        self.assertEqual(adj.hour, 7)

    def test_adjust_datetime_edge_cases(self):
        # min/max dates
        self.user.tz = "America/New_York"
        self.assertEqual(self.user.adjust_datetime(datetime.min, subtract=True), datetime.min)
        self.assertEqual(self.user.adjust_datetime(datetime.max, subtract=False), datetime.max)

        # OverflowError (though hard to trigger normally,
        # we can mock or just hope for coverage if hit)
        # Actually it handles it with try-except
        # To trigger OverflowError we can try adding a large timedelta to a large datetime
        # But adjust_datetime uses get_user_timezone_offset which is at most 14 hours.
        # So adding 14 hours to datetime.max - 1 hour should trigger it.
        large_dt = datetime.max - timedelta(hours=1)
        # If TZ is +14 (Pacific/Kiritimati)
        self.user.tz = "Pacific/Kiritimati"
        adj = self.user.adjust_datetime(large_dt, subtract=False)
        self.assertEqual(adj, large_dt)  # Should return dt on OverflowError
