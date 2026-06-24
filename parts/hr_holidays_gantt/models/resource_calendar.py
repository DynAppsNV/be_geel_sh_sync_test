from odoo import models
from datetime import datetime, time
from odoo.tools import float_compare


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _handle_flexible_leave_interval(self, dt0, dt1, leave):
        def at_time(d, hour=0, minute=0, second=0, microsecond=0):
            return datetime.combine(
                d.date(),
                time(hour, minute, second, microsecond)
            ).replace(tzinfo=tz)

        tz = dt0.tzinfo
        if leave.sudo().holiday_id.request_unit_half:
            dt0 = at_time(dt0) if leave.holiday_id.request_date_from_period == 'am' else at_time(dt0, 12)
            dt1 = at_time(dt1, 12) if leave.holiday_id.request_date_to_period == 'am' else at_time(dt1, 23, 59, 59, 999999)
            return dt0, dt1

        if leave.holiday_id.request_unit_hours:
            if float_compare(leave.holiday_id.number_of_hours, leave.calendar_id.hours_per_day, 2) == 0:
                return at_time(dt0), at_time(dt1, 23, 59, 59, 999999)

            if float_compare(leave.holiday_id.number_of_hours, leave.calendar_id.hours_per_day / 2, 2) == 0:
                if leave.holiday_id.request_hour_to <= 12.0:
                    return at_time(dt0), at_time(dt1, 12)
                if leave.holiday_id.request_hour_from >= 12.0:
                    return at_time(dt0, 12), at_time(dt1, 23, 59, 59, 999999)

        return super()._handle_flexible_leave_interval(dt0, dt1, leave)
