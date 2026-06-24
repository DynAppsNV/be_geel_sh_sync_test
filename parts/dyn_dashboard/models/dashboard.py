import logging

from psycopg2 import ProgrammingError

from odoo import api, fields, models
from odoo.exceptions import UserError

from .date_ranges import get_selection_date_range

_logger = logging.getLogger(__name__)


class DynDashboard(models.Model):
    _name = "xx.dashboard"
    _description = "DynApps Dashboard"
    _rec_name = "name"

    name = fields.Char()
    show_date_filter = fields.Boolean()
    graph_locale = fields.Char(help="Locale in format 'language-COUNTRY", default="nl-BE")
    dashboard_start_date = fields.Date()
    dashboard_end_date = fields.Date()

    date_filter_selection = fields.Selection(
        [
            ("l_none", "All Time"),
            ("l_days", "Today"),
            ("t_weeks", "This Week"),
            ("t_months", "This Month"),
            ("t_quarters", "This Quarter"),
            ("t_years", "This Year"),
            ("n_days", "Next Day"),
            ("n_weeks", "Next Week"),
            ("n_months", "Next Month"),
            ("n_quarters", "Next Quarter"),
            ("n_years", "Next Year"),
            ("ls_days", "Last Day"),
            ("ls_weeks", "Last Week"),
            ("ls_months", "Last Month"),
            ("ls_quarters", "Last Quarter"),
            ("ls_years", "Last Year"),
            ("l_weeks", "Last 7 days"),
            ("l_months", "Last 30 days"),
            ("l_quarters", "Last 90 days"),
            ("l_years", "Last 365 days"),
            ("ls_past_until_now", "Past Till Now"),
            ("ls_pastwithout_now", " Past Excluding Today"),
            ("n_future_starting_now", "Future Starting Now"),
            ("n_futurestarting_tomorrow", "Future Starting Tomorrow"),
            ("l_custom", "Custom Filter"),
        ],
        default="l_none",
        string="Default Date Filter",
    )

    xx_custom_filter_ids = fields.One2many(
        "xx.dyn.custom.filter", "dashboard_id", string="Custom Filters"
    )
    menu_name = fields.Char()
    menu_id = fields.Many2one("ir.ui.menu", readonly=True)
    parent_menu_id = fields.Many2one(
        "ir.ui.menu",
        default=lambda self: self.env.ref("dyn_dashboard.menu_dyn_dashboard_overview", False),
    )
    menu_action_id = fields.Many2one("ir.actions.act_window", readonly=True)

    tile_ids = fields.One2many("xx.dashboard.tile", "dashboard_id")
    drill_hierarchy = fields.Integer(compute="_compute_drill_hierarchy", store=True, recursive=True)

    @api.depends(
        "tile_ids", "tile_ids.xx_dashboard_drill", "tile_ids.xx_dashboard_drill.drill_hierarchy"
    )
    def _compute_drill_hierarchy(self):
        for record in self:
            res = sum(record.mapped("tile_ids.xx_dashboard_drill.drill_hierarchy")) + 1
            record.drill_hierarchy = res

    @api.model_create_multi
    def create(self, vals_list):
        try:
            res = super().create(vals_list)
            for dashboard in res:
                if dashboard.menu_name:
                    # create the menu item
                    action_vals = {
                        "res_model": "xx.dashboard",
                        "name": dashboard.menu_name,
                        "context": {"dashboard_id": dashboard.id},
                        "view_mode": "dyn_dashboard",
                        "view_id": self.env.ref("dyn_dashboard.xx_my_dashboard").id,
                    }
                    action_id = self.env["ir.actions.act_window"].sudo().create(action_vals)
                    dashboard.menu_action_id = action_id

                    menu_item_vals = {
                        "action": f"ir.actions.act_window,{action_id.id}",
                        "active": True,
                        "display_name": dashboard.menu_name,
                        "name": dashboard.menu_name,
                        "parent_id": dashboard.parent_menu_id and dashboard.parent_menu_id.id,
                        "sequence": 10,
                        "parent_path": dashboard.parent_menu_id
                        and dashboard.parent_menu_id.parent_path,
                    }
                    menu_item = self.env["ir.ui.menu"].sudo().create(menu_item_vals)
                    dashboard.menu_id = menu_item

        except ProgrammingError:
            raise UserError(self.env._("Error creating dashboard")) from None
        return res

    def write(self, values):
        res = super().write(values)

        # Update the menu name
        if "menu_name" in values:
            self.menu_id.sudo().name = values["menu_name"]
        # update parent menu
        if "parent_menu_id" in values:
            parent_id = self.env["ir.ui.menu"].browse(values["parent_menu_id"])
            parent_path = parent_id.parent_path
            self.menu_id.write({"parent_id": parent_id, "parent_path": parent_path})

        return res

    def unlink(self):
        """
        cascade delete since ondelete=cascade does not clear ir.model.data needed for
        importing dashboards
        """
        for rec in self:
            for tile in rec.tile_ids:
                tile.unlink()
            for custom_filter in rec.xx_custom_filter_ids:
                custom_filter.unlink()
            rec.menu_id.unlink()
        return super().unlink()

    @api.model
    def fetch_dashboard_data(self, dashboard_id):
        """
        Return Dictionary of Dashboard Data.
        :param dashboard_id: Integer
        :return: dict
        """
        self = self.set_dashboard_date(dashboard_id)
        dashboard = self.browse(dashboard_id)
        date_filter_selection = (
            self.env.context.get("dynDateFilterSelection", False) or dashboard.date_filter_selection
        )
        show_date_filter = dashboard.show_date_filter
        if show_date_filter and date_filter_selection == "l_custom":
            show_custom_date_filter = True
        else:
            show_custom_date_filter = False
        dashboard_data = {
            "dashboard_id": dashboard.id,
            "name": dashboard.name,
            "show_date_filter": show_date_filter,
            "show_custom_date_filter": show_custom_date_filter,
            "date_filter_selection": date_filter_selection,
            "dashboard_start_date": self.env.context.get("dynDateFilterStartDate", False)
            or dashboard.dashboard_start_date,
            "dashboard_end_date": self.env.context.get("dynDateFilterEndDate", False)
            or dashboard.dashboard_end_date,
            "tiles": [
                {
                    "name": x.name,
                    "type": x.display_type,
                    "tile_id": x.id,
                    "width": x.width,
                    "height": x.height,
                }
                for x in dashboard.tile_ids
            ],
            "tile_ids": dashboard.tile_ids.ids,
            "tile_data": {},
        }
        custom_filters = []
        for custom_filter in dashboard.xx_custom_filter_ids:
            custom_filter._compute_selections()
            user_filters = self.env["res.users"].browse(self.env.uid).xx_dyn_custom_filter_value_ids
            user_filter_value = False
            if not custom_filter.hidden:
                user_filter_value = user_filters.filtered(
                    lambda x, c=custom_filter: x.filter_id == c
                )
            filter_value = user_filter_value[0].value if user_filter_value else ""
            dashboard_id_orig = int(self.env.context.get("dashboard_id_orig", False))
            if dashboard_id_orig:
                filter_orig = user_filters.filtered(
                    lambda x, i=dashboard_id_orig, c=custom_filter: x.filter_id.filter_name
                    == c.filter_name
                    and x.filter_id.dashboard_id.id == i
                )
                if filter_orig:
                    filter_value = filter_orig.value
            selection = custom_filter.use_odoo_data or len(custom_filter.manual_selection_ids) > 0
            value = False
            if custom_filter.multiselect:
                value = filter_value.split(",") if filter_value else []
                value = [x for x in value if x != ""]
            else:
                value = filter_value
            custom_filters += [
                {
                    "name": custom_filter.filter_name,
                    "filter_id": custom_filter.id,
                    "selection": selection,
                    "multiselect": custom_filter.multiselect,
                    "minimum_input_for_select": custom_filter.minimum_input_for_select,
                    "value": value,
                    "hidden": custom_filter.hidden,
                }
            ]
        dashboard_data["custom_filters"] = custom_filters

        return dashboard_data

    @api.model
    def dyn_fetch_item(self, item_list, dashboard_id):
        """
        :rtype: object
        :param item_list: list of item ids.
        :return: {'id':[item_data]}
        """
        self = self.set_dashboard_date(dashboard_id)
        items = {}
        item_model = self.env["xx.dashboard.tile"]
        for item_id in item_list:
            item = item_model.browse(item_id).get_data()
            items[item_id] = item
        return items

    def set_dashboard_date(self, dashboard_id):
        start_date = False
        end_date = False

        if self.env.context.get("dynDateFilterSelection", False):
            date_filter_selection = self.env.context["dynDateFilterSelection"]
            if date_filter_selection == "l_custom":
                # no need to convert date using timezone as this has already been done
                start_date = fields.datetime.strptime(
                    self._context["dynDateFilterStartDate"], "%Y-%m-%dT%H:%M:%S.%fz"
                )
                end_date = fields.datetime.strptime(
                    self.env.context["dynDateFilterEndDate"], "%Y-%m-%dT%H:%M:%S.%fz"
                )
        else:
            # TODO : dashboard_id value not consistent:
            #  sometimes int, other times dashboard instance: this seems not correct
            if not isinstance(dashboard_id, int):
                dashboard_id = dashboard_id.id
            date_filter_selection = self.browse(dashboard_id).date_filter_selection
            # no need to convert date using timezone as this has already been done
            start_date = self.browse(dashboard_id).dashboard_start_date
            end_date = self.browse(dashboard_id).dashboard_end_date
            self = self.with_context(dynDateFilterSelection=date_filter_selection)

        if date_filter_selection not in ["l_custom", "l_none"]:
            selection_date_data = get_selection_date_range(date_filter_selection)
            start_date = self.env.user.adjust_datetime(selection_date_data["selected_start_date"])
            end_date = self.env.user.adjust_datetime(selection_date_data["selected_end_date"])

        added_context = {}
        if start_date:
            added_context["dynDateFilterStartDate"] = start_date
        if end_date:
            added_context["dynDateFilterEndDate"] = end_date
        if added_context:
            self = self.with_context(**added_context)
        return self

    @api.model
    def clear_filter_selections(self, dashboard_id):
        """Clears filter selections for given dashboard"""
        dashboard = self.sudo().browse(dashboard_id)
        for custom_filter in dashboard.xx_custom_filter_ids:
            if custom_filter.use_odoo_data:
                custom_filter.with_context(no_recompute=True).manual_selection_ids.unlink()
                custom_filter.with_context(no_recompute=True).selection_ids.unlink()

    def cron_clear_all_filter_selections(self):
        self.sudo().env["xx.dyn.custom.filter.selection"].search(
            [("filter_id.use_odoo_data", "=", True)]
        ).unlink()
