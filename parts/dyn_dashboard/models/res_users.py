from datetime import date, datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    xx_dyn_custom_filter_value_ids = fields.One2many(
        comodel_name="xx.dyn.custom.filter.value",
        inverse_name="user_id",
        string="Custom Filter Values",
    )
    xx_dyn_dashboard_last_selected_start_date = fields.Date(
        string="Last selected Start Date", default=fields.Date.today() + relativedelta(months=1)
    )
    xx_dyn_dashboard_last_selected_end_date = fields.Date(
        string="Last selected End Date", default=fields.Date.today() + relativedelta(months=1)
    )

    @api.model
    def fetch_initial_dyn_dashboard_date_range(self):
        user = self.env.user
        start_date = "xx_dyn_dashboard_last_selected_start_date"
        end_date = "xx_dyn_dashboard_last_selected_end_date"
        # Fetching field attributes for the specified field.
        rec_fields = user.fields_get([start_date, end_date])
        initial_values = {
            **self._get_user_value(start_date, user),
            **self._get_user_value(end_date, user),
        }

        return {
            "initial_values": initial_values,
            "fields": rec_fields,
        }

    def _get_user_value(self, field_name, user):
        # Fetching initial value for the specified field.
        value = user[field_name]
        # If date is before today, set it to today + 1 month.
        if value and value < fields.Date.today():
            value = fields.Date.today() + relativedelta(months=1)
            user[field_name] = value
        initial_values = {field_name: value}
        return initial_values

    def get_user_timezone_offset(self):
        """Calculate the user's timezone offset as a timedelta."""
        user_timezone = pytz.timezone(self.env.user.tz or "GMT")
        now = datetime.now(user_timezone)
        offset_str = now.strftime("%z")

        # Convert the offset to hours and minutes
        offset_hours = int(offset_str[:3])
        offset_minutes = int(offset_str[3:])

        return timedelta(
            hours=offset_hours, minutes=offset_minutes if offset_hours >= 0 else -offset_minutes
        )

    def adjust_datetime(
        self, datetime_value, format_datetime="%Y-%m-%dT%H:%M:%S.%fZ", subtract=True
    ):
        """
        Adjust a datetime string by subtracting or adding the user's timezone offset.
        This comes in handy when you want to query the DB for comparisons.

        :param datetime_value: The datetime value to adjust (can be a string or datetime object).
        :param format_datetime: The format of the input datetime string (default is ISO format).
        :param subtract: Boolean to specify whether to subtract (default) or add the offset_delta.
        :return: Adjusted datetime object or False if input is invalid.
        """
        if not datetime_value:
            return False

        # Parse the input datetime string if it is not already a datetime object
        if not isinstance(datetime_value, (datetime | date)):
            dt = datetime.strptime(datetime_value, format_datetime)
        else:
            dt = datetime_value

        # Get the user's timezone offset
        offset_delta = self.get_user_timezone_offset()

        # Adjust the datetime based on the subtract parameter
        adjusted_dt = dt
        try:
            if subtract:
                if dt != datetime.min:
                    adjusted_dt = dt - offset_delta
            else:
                if dt != datetime.max:
                    adjusted_dt = dt + offset_delta
        except OverflowError:
            adjusted_dt = dt

        return adjusted_dt
