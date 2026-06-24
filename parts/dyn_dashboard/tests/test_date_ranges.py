from datetime import datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase, tagged

from ..models import date_ranges


@tagged("-at_install", "post_install")
class TestDynDashboard(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.user

    def is_dst(self, timezone_str):
        # Get the timezone object using the timezone string
        tz = pytz.timezone(timezone_str)
        # Get the current time in the specified timezone
        current_time = datetime.now(tz)
        # Check if the timezone is in DST
        return bool(current_time.dst())

    def test_date_ranges(self):
        today = datetime.now().date()
        check_start_date = datetime(today.year, today.month, today.day)
        self.assertEqual(
            date_ranges.get_selection_date_range("l_day")["selected_start_date"],
            check_start_date,
            "l_day returns invalid value",
        )

        # check_start_date = datetime(today.year, today.month, today.day - 1)
        check_start_date = datetime(today.year, today.month, today.day) - timedelta(days=1)
        self.assertEqual(
            date_ranges.get_selection_date_range("ls_day")["selected_start_date"],
            check_start_date,
            "ls_day returns invalid value",
        )
        # check_start_date = datetime(today.year, today.month, today.day)
        check_start_date = datetime(today.year, today.month, today.day)
        self.assertEqual(
            date_ranges.get_selection_date_range("t_day")["selected_start_date"],
            check_start_date,
            "t_day returns invalid value",
        )

        check_start_date = datetime(today.year, today.month, today.day) + timedelta(days=1)
        self.assertEqual(
            date_ranges.get_selection_date_range("n_day")["selected_start_date"],
            check_start_date,
            "n_days returns invalid value",
        )

        check_start_date = datetime(today.year, today.month, today.day) + timedelta(days=1)
        self.assertEqual(
            date_ranges.get_date_range_from_day("next")["selected_start_date"],
            check_start_date,
            "next day returns invalid value",
        )
        check_start_date = datetime(today.year, today.month, today.day) - timedelta(days=1)
        self.assertEqual(
            date_ranges.get_date_range_from_day("previous")["selected_start_date"],
            check_start_date,
            "previous day returns invalid value",
        )

        check_start_date = datetime(today.year, today.month, today.day) + timedelta(days=7)
        self.assertEqual(
            date_ranges.get_date_range_from_week("next")["selected_start_date"],
            check_start_date - timedelta(days=check_start_date.weekday()),
            "next returns invalid value",
        )
        check_start_date = datetime(today.year, today.month, today.day) - timedelta(days=7)
        self.assertEqual(
            date_ranges.get_date_range_from_week("previous")["selected_start_date"],
            check_start_date - timedelta(days=check_start_date.weekday()),
            "previous week returns invalid value",
        )

        check_start_date = datetime(today.year, today.month, today.day) + relativedelta(months=1)
        self.assertEqual(
            date_ranges.get_date_range_from_month("next")["selected_start_date"],
            check_start_date - timedelta(days=check_start_date.day - 1),
            "next month returns invalid value",
        )
        check_start_date = datetime(today.year, today.month, today.day) + relativedelta(months=-1)
        self.assertEqual(
            date_ranges.get_date_range_from_month("previous")["selected_start_date"],
            check_start_date - timedelta(days=check_start_date.day - 1),
            "previous month returns invalid value",
        )

    def test_get_user_timezone_offset(self):
        """Test get_user_timezone_offset with various timezones."""

        test_cases = [
            ("UTC", timedelta(hours=0)),  # No offset
            ("Europe/Paris", timedelta(hours=1)),  # Positive offset
            ("America/New_York", timedelta(hours=-5)),  # Negative offset
            ("Asia/Kolkata", timedelta(hours=5, minutes=30)),  # Non-integer offset
        ]

        for tz_name, expected_delta in test_cases:
            if self.is_dst(tz_name):
                # timezone in dst has offset of 1 hour more than timezone in standard time
                expected_delta = expected_delta + timedelta(hours=1)
            self.user.tz = tz_name
            offset = self.user.get_user_timezone_offset()
            self.assertEqual(offset, expected_delta, f"Failed for timezone: {tz_name}")

    def test_adjust_datetime_real_objects(self):
        """Test adjust_datetime with real datetime objects."""
        test_cases = [
            ("UTC", datetime(2024, 11, 14, 12, 0, 0), datetime(2024, 11, 14, 12, 0, 0)),
            ("Europe/Paris", datetime(2024, 11, 14, 12, 0, 0), datetime(2024, 11, 14, 11, 0, 0)),
            # -1 hour
            (
                "America/New_York",
                datetime(2024, 11, 14, 12, 0, 0),
                datetime(2024, 11, 14, 17, 0, 0),
            ),
            # +5 hours
            ("Asia/Kolkata", datetime(2024, 11, 14, 12, 0, 0), datetime(2024, 11, 14, 6, 30, 0)),
            # -5h30
        ]

        for tz_name, input_dt, expected_dt in test_cases:
            if self.is_dst(tz_name):
                # date in dst is subtracted with 1 hour more than standard time
                expected_dt = expected_dt - timedelta(hours=1)
            self.user.tz = tz_name
            adjusted_dt = self.user.adjust_datetime(input_dt)
            self.assertEqual(adjusted_dt, expected_dt, f"Failed for timezone: {tz_name}")

    def test_adjust_datetime_strings(self):
        """Test adjust_datetime with string representations."""
        test_cases = [
            (
                "UTC",
                "2024-11-14T12:00:00.000Z",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                datetime(2024, 11, 14, 12, 0, 0),
            ),
            (
                "Europe/Paris",
                "2024-11-14 12:00:00",
                "%Y-%m-%d %H:%M:%S",
                datetime(2024, 11, 14, 11, 0, 0),
            ),
            (
                "America/New_York",
                "2024-11-14T12:00:00Z",
                "%Y-%m-%dT%H:%M:%SZ",
                datetime(2024, 11, 14, 17, 0, 0),
            ),
            (
                "Asia/Kolkata",
                "2024-11-14 12:00",
                "%Y-%m-%d %H:%M",
                datetime(2024, 11, 14, 6, 30, 0),
            ),
        ]

        for tz_name, input_str, fmt, expected_dt in test_cases:
            if self.is_dst(tz_name):
                # date in dst is subtracted with 1 hour more than standard time
                expected_dt = expected_dt - timedelta(hours=1)
            self.user.tz = tz_name
            adjusted_dt = self.user.adjust_datetime(input_str, fmt)
            self.assertEqual(
                adjusted_dt, expected_dt, f"Failed for timezone: {tz_name}, Input: {input_str}"
            )

    def test_invalid_input(self):
        """Test adjust_datetime with invalid inputs."""
        self.user.tz = "UTC"

        # None input
        result = self.user.adjust_datetime(None)
        self.assertFalse(result, "Expected False for None input")

        # Invalid datetime string
        with self.assertRaises(ValueError):
            self.user.adjust_datetime("Invalid Date String", "%Y-%m-%dT%H:%M:%S.%fZ")
