import datetime as dt
import json
import logging
from datetime import datetime

from dateutil import parser
from psycopg2 import ProgrammingError

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import numpy as np
    import pandas as pd
except (OSError, ImportError) as err:  # pragma: no cover
    _logger.debug(err)


class DynDashboardTile(models.Model):
    _name = "xx.dashboard.tile"
    _order = "sequence"
    _description = "DynApps Dashboard Tile"

    sequence = fields.Integer()
    name = fields.Char(help="This will appear in the red bar of the tile")
    dashboard_id = fields.Many2one(comodel_name="xx.dashboard")

    # Graph type + options
    display_type = fields.Selection(
        selection=[
            ("kpi", "kpi"),
            ("line_chart", "Line Chart"),
            ("bar_chart", "Bar Chart"),
            ("pie", "Pie Chart"),
            ("donut", "Donut Chart"),
            ("radial_bar", "Radial Bar"),
            ("text", "Text"),
            ("table", "Table"),
            ("dummy", "Dummy"),
        ]
    )
    graph_locale = fields.Char(
        help="Value to overwrite dashboard locale in format 'language-COUNTRY", default="nl-BE"
    )

    model_id = fields.Many2one(
        "ir.model",
        domain="[('model','not ilike','xx.dashboard%'),"
        "('model','not ilike','base_import%'),"
        "('access_ids','!=',False),('transient','=',False),"
        "('model','!=','mail.thread'),('model','not ilike','web_editor.%'),"
        "('model','not ilike','ir.%'),"
        "('model','not ilike','web_tour.%')]",
    )
    has_res_model = fields.Boolean(compute="_compute_has_res_model")
    new_tab = fields.Boolean("Open new tab", default=True)

    query = fields.Text()
    query_key_ids = fields.One2many(
        "xx.dashboard.query.field",
        "dashboard_tile_id",
        compute="_compute_query",
        store=True,
    )
    query_result = fields.Char()

    sub_title = fields.Char(help="Title shown within the graph")
    direction = fields.Selection(selection=[("vertical", "Vertical"), ("horizontal", "Horizontal")])
    is_stacked = fields.Boolean(help="Only applicable for bar/mixed charts")
    stacked_type = fields.Selection(selection=[("normal", "Normal"), ("100%", "100 %")])

    is_area = fields.Boolean(help="Only applicable for line charts")

    show_labels = fields.Boolean(help="Show/Hide labels on the bars/parts of pie/donut.")
    show_legend = fields.Boolean(help="Show/Hide legend on the charts.")
    show_markers = fields.Boolean(help="Show/Hide markers on the line charts.")
    is_radial_semi_circle = fields.Boolean(help="When true data is displayed as half a circle.")

    # Text field for the plain text tile
    plain_text = fields.Text(help="Tile can be use to show a simple text message")

    # Styling options: width/height/colors/font-size/graph theme
    width = fields.Integer("Width (cols)")
    height = fields.Integer("Height (rows)")
    icon = fields.Char(help="Use the font awesome class name. E.g. 'fa-thermometer-full'")
    icon_size = fields.Char(string="Icon size (in px)", default="20")

    bg_color = fields.Char(
        string="Background color", default="#fff", help="Hex-code or named color"
    )
    bg_color_header = fields.Char(
        string="Header Background color",
        default="linear-gradient(150deg, #542D4B 0%, #FFFFFF 90%)",
        help="Hex-code or named color",
    )
    font_color_title = fields.Char(
        string="Title Font color", default="#fff", help="Hex-code or named color"
    )
    font_size_title = fields.Char(string="Title Font size (in px)", default="20")

    font_color_text = fields.Char(
        string="Text Font color", default="#000", help="Hex-code or named color"
    )
    font_size_text = fields.Char(string="Text Font size (in px)", default="30")

    custom_color_array = fields.Text(
        default="#5DA5DA,#FAA43A,#60BD68,#F17CB0,#B2912F,#B276B2,#DECF3F,#F15854,#4D4D4D",
        help="Provide as a comma separated list of hex or rgb/rgba format"
        "if set it overrules the setting 'graph theme palette'"
        "As default the stephenFew colors are set",
    )

    graph_theme_palette = fields.Selection(
        selection=[
            ("palette1", "palette1"),
            ("palette2", "palette2"),
            ("palette3", "palette3"),
            ("palette4", "palette4"),
            ("palette5", "palette5"),
            ("palette6", "palette7"),
            ("palette7", "palette7"),
            ("palette8", "palette8"),
            ("palette9", "palette9"),
            ("palette10", "palette10"),
        ]
    )
    # Table settings
    table_format_params = fields.Text(help="Formatter config for the table tile")
    download_data = fields.Boolean(help="Show buttons to download data in CSV/XLSX/PDF/JSON file")
    pdf_orientation = fields.Selection(
        selection=[("landscape", "Landscape"), ("portrait", "Portrait")],
        default="landscape",
        help="Page orientation of the PDF data export",
    )
    # Drill action settings
    drill_type = fields.Selection(
        [("filter", "Filter"), ("dashboard", "Dashboard"), ("model", "Model")]
    )
    xx_dashboard_drill = fields.Many2one(
        comodel_name="xx.dashboard",
        string="Dashboard Action",
        domain="[('menu_action_id', '!=', False)]",
    )
    xx_dashboard_action = fields.Many2one(related="xx_dashboard_drill.menu_action_id")
    text_align_header = fields.Selection(
        string="Header alignment",
        selection=[("left", "Left"), ("center", "Center"), ("right", "Right")],
        default="left",
        help="Select the alignment of this field in the Grid view",
    )
    filter_drill = fields.Many2one(
        "xx.dyn.custom.filter",
        string="Filter",
        help="Filter name to be set on drill action",
        domain="[('dashboard_id', '=', dashboard_id),('hidden','=', True),]",
    )

    @api.depends("query_key_ids")
    def _compute_has_res_model(self):
        for rec in self:
            rec.has_res_model = rec.query_key_ids.filtered(lambda r: r.name == "res_model")

    def get_locale(self):
        return self.graph_locale or self.dashboard_id.graph_locale

    def query_wildcard_replace(self, query):
        self.ensure_one()
        start_date = self.env.context.get("dynDateFilterStartDate", False) or datetime.min
        end_date = self.env.context.get("dynDateFilterEndDate", False) or datetime.max
        # for date-fields, no timezone-correction needs to be made. We need to re-calculate here
        # as it depended on what kind of filter is set if the given date needed to be adjusted
        # to timezone or not. Check code of dashboard->set_dashboard_date()
        start_date_no_timezone_adjustment = self.env.user.adjust_datetime(
            start_date, subtract=False
        )
        end_date_no_timezone_adjustment = self.env.user.adjust_datetime(end_date, subtract=False)
        if isinstance(start_date, str):
            start_date = parser.isoparse(start_date)
        if isinstance(end_date, str):
            end_date = parser.isoparse(end_date)
        query = (
            query.replace(
                "%DATESTART",
                "'" + datetime.strftime(start_date_no_timezone_adjustment, "%Y-%m-%d") + "'",
            )
            .replace(
                "%DATEEND",
                "'" + datetime.strftime(end_date_no_timezone_adjustment, "%Y-%m-%d") + "'",
            )
            .replace(
                "%TIMESTAMPSTART", "'" + datetime.strftime(start_date, "%Y-%m-%d %H:%M:%S") + "'"
            )
            .replace("%TIMESTAMPEND", "'" + datetime.strftime(end_date, "%Y-%m-%d %H:%M:%S") + "'")
            .replace("%UID", str(self.env.user.id))
            .replace("%MYCOMPANY", str(self.env.user.company_id.id))
            .replace(
                "%MYCOMPANIES", f"({', '.join(str(x) for x in self.env.user.company_ids.ids)})"
            )
        )

        if query:
            wildcard_filters = self.dashboard_id.xx_custom_filter_ids.filtered(
                lambda x: x.query_wildcard_replace
            )
            for wildcard_filter in wildcard_filters:
                filter_value = self.env.context.get("dynCustomFilters") and next(
                    (
                        d["value"]
                        for d in self.env.context.get("dynCustomFilters")
                        if d["filter_id"] == wildcard_filter.id
                    ),
                    None,
                )
                if filter_value and isinstance(filter_value, list):
                    filter_value = [x for x in filter_value if x != ""]
                    if not filter_value:
                        filter_value = False
                    elif all(isinstance(x, int) for x in filter_value):
                        filter_value = ",".join(map(str, filter_value))
                    else:
                        filter_value = ",".join(f"'{x}'" for x in filter_value)
                elif isinstance(filter_value, str) and (
                    filter_value == "" or filter_value == "['']" or filter_value == "[]"
                ):
                    filter_value = False
                elif filter_value and isinstance(filter_value, str):
                    # Different possibilities for string values in filters.
                    # When the value is of type str, the filter is free text or single select.
                    # 1. In case of free text 'ilike' is possible so we also assume the string will
                    #    be enclosed by quotes in the query already.
                    # 2. In case of single select, we assume the exact value is selected so ilike
                    #    is not possible in the query.  Since multi-/single select can be turned on
                    #    or off we assume the query still can contain an IN clause which means the
                    #    string cannot be enclosed by quotes in the query.

                    if (
                        wildcard_filter.manual_selection_ids
                        and " ilike " not in wildcard_filter.query_wildcard_replace
                    ):
                        filter_value = f"'{filter_value}'"

                if filter_value:
                    query = query.replace(wildcard_filter.wildcard, filter_value)
                else:
                    query = query.replace(wildcard_filter.query_wildcard_replace, "1=1")
        return query

    @api.depends("drill_type")
    def _clear_drill_settings(self):
        self.xx_dashboard_drill = False
        self.xx_dashboard_action = False
        self.model_id = False
        self.new_tab = False
        self.filter_drill = False

    @api.depends("query")
    def _compute_query(self):
        for rec in self:
            rec.compute_query_key_ids(hasattr(rec, "_origin") and rec._origin)

    def compute_query_key_ids(self, origin=False):
        self.ensure_one()
        # Run when custom_query is changed
        # goal is to get a JSON with headers and one with all the records,
        # the headers will be used to set the labels
        # for rec in self:
        if self.query and self.display_type != "text":
            try:
                # Get the columns from the query
                columns, self.query_result = self.query_json_dump()
                # save the query result
                # get all known fields, fields with the same name remain,
                # new fields need to be added, fields no longer in the query need to be dropped
                sequence = 0
                currFields = self.get_query_key_ids(origin)
                if currFields:
                    sequence = len(currFields) - 1
                # create a query_field for each field in the result
                query_key_ids = list()
                for col in columns:
                    if not currFields or col not in currFields.mapped("name"):
                        values = {
                            "name": col,
                            "field_label": col.title(),
                            "sequence": sequence,
                        }
                        query_key_ids.append((0, 0, values))
                        sequence += 1
                # all new fields are added, the existing ones remain,
                # now delete the remaining field names from the currFields
                for field in currFields:
                    if field.name not in columns:
                        query_key_ids.append((2, field.id))
                    else:
                        query_key_ids.append((4, field.id))
                self.write({"query_key_ids": query_key_ids})
            except ProgrammingError as sqlerr:
                msgline1 = self.env._("Invalid query in")
                msgline2 = f" dashboard {self.dashboard_id.name} tile {self.name}:\n{sqlerr}\n"
                msgline3 = ""
                if sqlerr.pgcode == "42P01":
                    msgline3 = self.env._("Make sure all necessary modules are installed")
                raise UserError(msgline1 + msgline2 + msgline3) from sqlerr
        else:
            query_key_ids = list()
            for key in self.get_query_key_ids(origin):
                query_key_ids.append((1, key.id, {"name": False}))
            self.query_key_ids = query_key_ids
            self.query_result = False

    def get_query_key_ids(self, origin):
        tile_id = self.id or origin and origin.id
        query_key_ids = (
            tile_id
            and self.env["xx.dashboard.query.field"].search([("dashboard_tile_id", "=", tile_id)])
            or list()
        )
        return query_key_ids

    def query_json_dump(self):
        def default(o):
            if isinstance(o, dt.date | dt.datetime):
                return o.isoformat(" ", "seconds")

        query = self.query_wildcard_replace(self.query)
        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()

        columns = [x.name for x in self.env.cr.description]
        return columns, json.dumps({"records": self.update_timezone(res)}, default=default)

    def update_timezone(self, values):
        for rec in values:
            for key, val in rec.items():
                if type(val) is datetime:
                    rec[key] = self.env.user.adjust_datetime(val, subtract=False)

        return values

    def _refresh_query_result(self):
        # Refresh the data shown on the dashboard
        for rec in self:
            if rec.query and rec.display_type != "text":
                try:
                    # Get the columns from the query
                    columns, rec.query_result = self.query_json_dump()

                except Exception as e:
                    raise ValidationError(self.env._("Error refreshing query : %s", e)) from e
            else:
                rec.query_result = False
                rec.query_key_ids.name = False

    def get_row_data_drill_action(self, row_id, res_model=None):
        self.ensure_one()
        data = {
            "drill_type": self.drill_type,
        }
        if self.drill_type == "dashboard" and self.xx_dashboard_drill:
            data["xx_dashboard_drill"] = self.xx_dashboard_drill.id
            action_vals = {
                "res_model": "xx.dashboard",
                "name": self.xx_dashboard_drill.menu_action_id.sudo().name,
                "view_mode": "dyn_dashboard",
                "context": {
                    "dashboard_id": self.xx_dashboard_drill.id,
                    "dashboard_id_orig": self.dashboard_id.id,
                },
            }

            params = "params" in self.xx_dashboard_action and self.xx_dashboard_action.params or {}
            params.update(
                {
                    "dashboard_id_orig": self.dashboard_id.id,
                    "dyn_date_filter_selection_orig": self.env.context.get(
                        "dynDateFilterSelection"
                    ),
                    "dyn_dashboard_start_date": self.env.context.get("dynDateFilterStartDate"),
                    "dyn_dashboard_end_date": self.env.context.get("dynDateFilterEndDate"),
                }
            )
            action_vals["params"] = params
            data["new_tab"] = self.new_tab
        elif self.drill_type == "model" and self.model_id and row_id and not res_model:
            data["model_name"] = self.model_id.sudo().name
            data["model_model"] = self.model_id.sudo().model
            data["target_id"] = row_id
            data["new_tab"] = self.new_tab
        elif self.drill_type == "model" and res_model and row_id:
            model = self.env["ir.model"]._get(res_model)
            data["model_name"] = model.name
            data["model_model"] = model.model
            data["target_id"] = row_id
            data["new_tab"] = self.new_tab
        elif self.drill_type == "filter":
            data["filter_drill"] = self.filter_drill.id
            data["target_id"] = row_id
        else:
            return False

        data.update(
            {
                "xx_dashboard_drill": self.xx_dashboard_drill if self.xx_dashboard_drill else False,
                "xx_dashboard_action": action_vals if self.xx_dashboard_drill else False,
            }
        )

        return data

    def get_data(self):
        self.ensure_one()
        data = {}
        graph_data_template = {
            "options": {
                "chart": {
                    "width": "100%",
                    "background": "#fff",
                    "zoom": {"enabled": False, "type": "xy"},
                    "redrawOnWindowResize": True,
                    "redrawOnParentResize": True,
                },
                "series": [],
                "grid": {"row": {"colors": ["#f3f3f3", "transparent"], "opacity": 0.5}},
                "stroke": {"show": True, "curve": "smooth", "width": 2},
                "fill": {"opacity": 1},
                "title": {"align": "center", "floating": False, "style": {"fontWeight": "bold"}},
                "legend": {"show": False},
                "markers": {"size": 0},
                "dataLabels": {"enabled": False},
            },
        }

        if self.display_type == "line_chart":
            data = self.get_line_chart_data(graph_data_template)
        elif self.display_type == "bar_chart":
            data = self.get_bar_chart_data(graph_data_template)
        elif self.display_type == "kpi":
            data = self.get_kpi_data()
        elif self.display_type == "pie":
            data = self.get_pie_chart_data(graph_data_template, "pie")
        elif self.display_type == "donut":
            data = self.get_pie_chart_data(graph_data_template, "donut")  # pragma: no cover
        elif self.display_type == "radial_bar":
            data = self.get_radial_bar_chart_data(graph_data_template)
        elif self.display_type == "text":
            data = self.get_text_data()
        elif self.display_type == "table":
            data = self.get_table_data()
        elif self.display_type == "dummy":
            data = self.get_dummy_data()

        if self.xx_dashboard_drill:
            data["xx_dashboard_drill"] = self.xx_dashboard_drill.id
            action_vals = {
                "res_model": "xx.dashboard",
                "name": self.xx_dashboard_drill.menu_action_id.sudo().name,
                "view_mode": "dyn_dashboard",
                "context": {"dashboard_id": self.xx_dashboard_drill.id},
            }
        elif self.model_id:
            data["model_name"] = self.model_id.sudo().name
            data["model_model"] = self.model_id.sudo().model

        icon = ""
        if self.icon:
            icon = "fa " + self.icon

        data.update(
            {
                "bg_color": self.bg_color,
                "bg_color_header": self.bg_color_header,
                "text_align_header": self.text_align_header,
                "width": self.width,
                "height": self.height,
                "icon": icon,
                "icon_size": self.icon_size,
                "font_size_title": self.font_size_title,
                "font_color_title": self.font_color_title,
                "xx_dashboard_drill": self.xx_dashboard_drill if self.xx_dashboard_drill else False,
                "xx_dashboard_action": action_vals if self.xx_dashboard_drill else False,
                "drill_type": self.drill_type,
                "filter_drill": self.filter_drill.id,
                "new_tab": self.new_tab,
            }
        )

        return data

    def get_line_chart_data(self, data_template):
        self.ensure_one()

        all_series_data = {}
        # Get the first field marked to show on the X-axis - if none is marked,
        # break from the function
        xAxisField = next(
            iter(self.query_key_ids.filtered(lambda x: x.show_on_axis == "xaxis") or []), ""
        )

        for x in self.query_key_ids.filtered(lambda x: x.show_on_axis == "xaxis"):
            xAxisField = x.name
            break

        if xAxisField == "":
            return {"Error": "Select a Field to show on the X-Axis"}

        # Initialise the graph setting and fill later in the function
        graph_data = data_template

        graph_data["id"] = self.id
        graph_data["type"] = "line_chart"
        graph_data["name"] = self.name
        graph_data["locale"] = self.get_locale()
        graph_data["options"]["chart"]["stacked"] = self.is_stacked
        graph_data["options"]["chart"]["type"] = "line"
        graph_data["options"]["chart"]["stackType"] = self.stacked_type if self.stacked_type else ""

        graphHeight = 100
        margin = 65
        if int(self.font_size_title) > 0:
            margin = margin + int(self.font_size_title)
        if self.height > 1:
            graphHeight = (100 + (self.height - 1) * 110) - margin

        graph_data["options"]["chart"]["height"] = graphHeight
        graph_data["options"]["theme"] = {"palette": self.graph_theme_palette}

        # DATA
        # flake8: noqa: C901
        for x in self.query_key_ids.filtered(lambda y: y.show_on_axis != "xaxis"):
            if x.show_on_axis == "legend":
                continue  # TODO legend need different dict for 2 dimensions [DYNUPGR-411]

            all_series_data[x.name] = {
                "data": [],
                "name": x.name,
                "type": x.type_output,
            }

            if x.show_on_axis == "yaxis":
                if "yaxis" not in graph_data["options"]:
                    graph_data["options"]["yaxis"] = []

                graph_data["options"]["yaxis"].append(
                    {
                        "seriesName": x.name,
                        "opposite": x.opposite_axis_label,
                        "axisTicks": {"show": True, "color": x.axis_label_color},
                        "axisBorder": {"show": True, "color": x.axis_label_color},
                        "title": {"text": x.field_label, "style": {"color": x.axis_label_color}},
                    }
                )

        # Reload the actual data of the query without recalculating the fields...
        self._refresh_query_result()

        # Get all values - there might be more then 1 value : so for each value a bar
        for rec in json.loads(self.query_result)["records"]:
            # Get the LABELS for the x-axis: E.G the name of each item : apples, pears, oranges,
            # OR month if showing stats per month
            if "xaxis" not in graph_data["options"]:
                graph_data["options"]["xaxis"] = {"categories": []}

            graph_data["options"]["xaxis"]["categories"].append(rec[xAxisField])

            # Get the VALUES of each item : 7, 5, 9
            for x in self.query_key_ids:
                # TODO legend needs to be processed different [DYNUPGR-411]
                if x.name != xAxisField and x.show_on_axis != "legend":
                    all_series_data[x.name]["data"].append(rec[x.name])

        for x in all_series_data:
            graph_data["options"]["series"].append(all_series_data[x])

        if self.is_stacked:
            column_data = [
                all_series_data[x]["data"]
                for x in all_series_data
                if all_series_data[x]["type"] == "column"
            ]
            if sum([len(all_series_data[x]["data"]) for x in all_series_data]) > 0:
                maxvalue = (
                    max(
                        max([max(all_series_data[x]["data"], default=0) for x in all_series_data]),
                        np.sum([[j if j >= 0 else 0 for j in i] for i in column_data], 0).max(),
                    )
                    * 1.1
                )
                yaxis_max = {"max": maxvalue}
                if "yaxis" not in graph_data["options"]:
                    graph_data["options"]["yaxis"] = yaxis_max
                else:
                    for y in graph_data["options"]["yaxis"]:
                        y.update(yaxis_max)

        if self.sub_title:
            # The entered subtitle will be added as title on the graph - as the real
            # title is in the header
            graph_data["options"]["title"] = {
                "text": self.sub_title,
                "align": "center",
                "floating": False,
                "style": {
                    "fontSize": "%s px" % (int(self.font_size_title) - 2),
                    "color": self.font_color_title,
                },
            }

        if self.show_legend:
            graph_data["options"]["legend"] = {
                "show": True,
                "showForSingleSeries": True,
                "horizontalAlign": "left",
            }

        if self.show_markers:
            graph_data["options"]["markers"] = {"size": 4}

        if self.show_labels:
            graph_data["options"]["dataLabels"] = {"enabled": True, "position": "top"}

        if self.is_area:
            graph_data["options"]["type"] = "area"
        else:
            graph_data["options"]["type"] = "line"

        if self.custom_color_array:
            graph_data["options"]["colors"] = [v for v in self.custom_color_array.split(",")]

        return graph_data

    # flake8: noqa: C901
    def get_bar_chart_data(self, data_template):
        self.ensure_one()

        all_series_data = {}
        xaxis_labels = []

        # Get the first field marked to show on the X-axis - if none is marked,
        # break from the function
        xAxisField = next(
            iter(self.query_key_ids.filtered(lambda x: x.show_on_axis == "xaxis") or []), ""
        )

        for x in self.query_key_ids.filtered(lambda x: x.show_on_axis == "xaxis"):
            xAxisField = x.name
            break

        if xAxisField == "":
            return {"Error": "Select a Field to show on the X-Axis"}

        legend_field = None
        for x in self.query_key_ids.filtered(lambda x: x.show_on_axis == "legend"):
            legend_field = x.name
            break

        graph_data = data_template

        graph_data["id"] = self.id
        graph_data["type"] = "line_chart"
        graph_data["name"] = self.name
        graph_data["locale"] = self.get_locale()

        graph_data["options"]["chart"]["type"] = "bar"
        graph_data["options"]["chart"]["stacked"] = self.is_stacked
        graph_data["options"]["chart"]["stackType"] = self.stacked_type if self.stacked_type else ""

        graphHeight = 100
        margin = 65
        if int(self.font_size_title) > 0:
            margin = margin + int(self.font_size_title)
        if self.height > 1:
            graphHeight = (100 + (self.height - 1) * 110) - margin

        graph_data["options"]["chart"]["height"] = graphHeight
        graph_data["options"]["xaxis"] = {"categories": xaxis_labels}
        graph_data["options"]["theme"] = {"palette": self.graph_theme_palette}
        graph_data["options"]["stroke"]["width"] = 0

        # DATA
        for x in self.query_key_ids.filtered(lambda y: y.show_on_axis != "xaxis"):
            all_series_data[x.name] = {
                "name": x.name,
                "data": [],
                "type": x.type_output,
            }

            if x.show_on_axis == "yaxis":
                if "yaxis" not in graph_data["options"]:
                    graph_data["options"]["yaxis"] = []

                graph_data["options"]["yaxis"].append(
                    {
                        "seriesName": x.name,
                        "opposite": x.opposite_axis_label,
                        "axisTicks": {"show": True, "color": x.axis_label_color},
                        "axisBorder": {"show": True, "color": x.axis_label_color},
                    }
                )

        # Reload the actual data of the query without recalculating the fields...
        self._refresh_query_result()
        not_on_axis = self.query_key_ids.filtered(lambda x: not x.show_on_axis).mapped("name")
        if len(not_on_axis) == 1:
            not_on_axis = not_on_axis[0]
        records = pd.DataFrame(json.loads(self.query_result)["records"])
        if len(records):
            # In case a legend field is defined; the dataset needs to be pivoted
            if legend_field:
                df = records.pivot(xAxisField, legend_field, not_on_axis)
                categories = df.index.values.tolist()
            else:
                df = records
                categories = df[xAxisField].values.tolist()

            series = list()
            for x in [x for x in df if x != xAxisField]:
                name = x
                data = df[x].fillna(0).values.tolist()
                series.append({"name": name, "data": data, "type": "column"})
            graph_data["options"]["series"] = series
            graph_data["options"]["xaxis"] = {
                "categories": categories,
            }

        if self.sub_title:
            # The entered subtitle will be added as title on the graph - as the real title is in
            # the header
            graph_data["options"]["title"] = {
                "text": self.sub_title,
                "align": "center",
                "floating": False,
                "style": {
                    "fontSize": "%s px" % (int(self.font_size_title) - 2),
                    "color": self.font_color_title,
                },
            }

        if self.direction == "horizontal":
            graph_data["options"]["plotOptions"] = {"bar": {"horizontal": True}}

        if self.show_legend:
            graph_data["options"]["legend"] = {
                "show": True,
                "showForSingleSeries": True,
                "horizontalAlign": "left",
            }
        else:
            graph_data["options"]["legend"] = {"show": False}

        if self.show_markers:
            graph_data["options"]["markers"] = {"size": 4}

        if self.show_labels:
            graph_data["options"]["dataLabels"] = {
                "enabled": True,
                "offsetX": -5 if self.direction == "horizontal" else 0,
                "position": "top",
            }

        if self.custom_color_array:
            graph_data["options"]["colors"] = [v for v in self.custom_color_array.split(",")]

        return graph_data

    def get_pie_chart_data(self, data_template, pie_type="pie"):
        self.ensure_one()

        # Get the first field marked to show on the X-axis - if none is marked,
        # break from the function
        xAxisField = next(
            iter(self.query_key_ids.filtered(lambda x: x.show_on_axis == "xaxis") or []), ""
        )

        for x in self.query_key_ids.filtered(lambda x: x.show_on_axis == "xaxis"):
            xAxisField = x.name
            break

        if xAxisField == "":
            return {"Error": "Select a Field to show on the X-Axis"}

        graph_data = data_template

        graph_data["id"] = self.id
        graph_data["type"] = "pie_chart"
        graph_data["name"] = self.name
        graph_data["locale"] = self.get_locale()

        graphHeight = 93
        margin = 65
        if int(self.font_size_title) > 0:
            margin = margin + int(self.font_size_title)
        if self.height > 1:
            graphHeight = (93 + (self.height - 1) * 110) - margin

        graph_data["options"]["chart"]["height"] = graphHeight
        graph_data["options"]["chart"]["type"] = pie_type
        graph_data["options"]["theme"] = {"palette": self.graph_theme_palette}
        graph_data["options"]["labels"] = []

        # Reload the actual data of the query without recalculating the fields...
        self._refresh_query_result()

        # Get all values - there might be more then 1 value : so for each value a bar
        for rec in json.loads(self.query_result)["records"]:
            # Get the values for the x-axis: E.G the name of each item : apples, pears, oranges,
            # OR month if showing stats per month
            graph_data["options"]["labels"].append(rec[xAxisField])

            # the value of each item : 7, 5, 9
            for x in self.query_key_ids:
                if x.name != xAxisField:
                    graph_data["options"]["series"].append(rec[x.name])

        if self.show_labels:
            graph_data["options"]["dataLabels"] = {"enabled": True, "position": "top"}

        if self.sub_title:
            # The entered subtitle will be added as title on the graph - as the real
            # title is in the header
            graph_data["options"]["title"] = {
                "text": self.sub_title,
                "align": "center",
                "floating": False,
                "style": {
                    "fontSize": "%s px" % (int(self.font_size_title) - 2),
                    "color": self.font_color_title,
                },
            }

        if self.is_radial_semi_circle:
            graph_data["options"]["plotOptions"] = {pie_type: {"startAngle": -90, "endAngle": 90}}

        if self.show_legend:
            graph_data["options"]["legend"] = {
                "show": True,
                "showForSingleSeries": True,
                "horizontalAlign": "left",
            }

        if self.custom_color_array:
            graph_data["options"]["colors"] = [v for v in self.custom_color_array.split(",")]

        return graph_data

    def get_radial_bar_chart_data(self, data_template):
        self.ensure_one()

        x_axis_filtered = self.query_key_ids.filtered(lambda x: x.show_on_axis == "xaxis")
        x_axis_field = x_axis_filtered[0] if x_axis_filtered else ""
        y_axis_filtered = self.query_key_ids.filtered(lambda x: x.show_on_axis == "yaxis")
        y_axis_field = y_axis_filtered[0] if y_axis_filtered else ""

        if not x_axis_field or not y_axis_field:
            return {"Error": "Select a Field to show on the X-Axis and Y-Axis"}

        x_axis_field = x_axis_field.field_label
        y_axis_field = y_axis_field.field_label

        graph_data = data_template

        graph_data["id"] = self.id
        graph_data["type"] = "radial_bar_chart"
        graph_data["name"] = self.name
        graph_data["locale"] = self.get_locale()

        graphHeight = 93
        margin = 65
        if int(self.font_size_title) > 0:
            margin = margin + int(self.font_size_title)
        if self.height > 1:
            graphHeight = (93 + ((self.height - 1) * 110)) - margin

        graph_data["options"]["chart"]["height"] = graphHeight
        graph_data["options"]["chart"]["type"] = "radialBar"
        graph_data["options"]["theme"] = {"palette": self.graph_theme_palette}
        graph_data["options"]["labels"] = []

        # Reload the actual data of the query without recalculating the fields...
        self._refresh_query_result()

        # Get all values - there might be more then 1 value : so for each value a bar
        for rec in json.loads(self.query_result)["records"]:
            graph_data["options"]["labels"].append(rec[x_axis_field])
            graph_data["options"]["series"].append(rec[y_axis_field])

        graph_data["options"]["series"] = self.calculate_relative_percentage(
            graph_data["options"]["series"]
        )

        if self.show_labels:
            graph_data["options"]["dataLabels"] = {"enabled": True, "position": "top"}

        if self.sub_title:
            # The entered subtitle will be added as title on the graph - as the real title is in
            # the header
            graph_data["options"]["title"] = {
                "text": self.sub_title,
                "align": "center",
                "floating": False,
                "style": {
                    "fontSize": "%s px" % (int(self.font_size_title) - 2),
                    "color": self.font_color_text,
                },
            }

        if self.is_radial_semi_circle:
            graph_data["options"]["plotOptions"] = {
                "radialBar": {"startAngle": -90, "endAngle": 90}
            }
            if self.show_labels:
                # special positioning for the semi-circle radial
                graph_data["options"]["plotOptions"]["radialBar"]["dataLabels"] = {
                    "show": True,
                    "name": {
                        "show": True,
                        "offsetY": 32,
                        "fontSize": f"{int(self.font_size_text)}px",
                    },
                    "value": {
                        "show": True,
                        "offsetY": -16,
                        "fontSize": f"{int(self.font_size_text)}px",
                        "color": self.font_color_text,
                    },
                }
            else:
                graph_data["options"]["plotOptions"]["radialBar"]["dataLabels"] = {
                    "show": True,
                    "name": {"show": False},
                    "value": {
                        "show": True,
                        "offsetY": 0,
                        "fontSize": f"{int(self.font_size_text)}px",
                        "color": self.font_color_text,
                    },
                }

        if self.show_legend:
            graph_data["options"]["legend"] = {
                "show": True,
                "showForSingleSeries": True,
                "horizontalAlign": "left",
            }

        if self.custom_color_array:
            graph_data["options"]["colors"] = [v for v in self.custom_color_array.split(",")]

        return graph_data

    def get_kpi_data(self):
        # KPI expects 1 number
        self.ensure_one()

        # qry_keys = json.loads(self.query_key_ids.name)
        if len(self.query_key_ids) != 1:
            # validate ?
            pass

        # Reload the actual data of the query without recalculating the fields...
        self._refresh_query_result()

        drill_ids = False
        val = 0

        if self.query_result:
            # get only one value for a kpi that is not the 'ids'
            for rec in json.loads(self.query_result)["records"]:
                drill_ids = rec.get("ids") and [int(i) for i in rec.pop("ids").split(",")] or list()
                val = [x for x in rec.values()][0]
        return {
            "id": self.id,
            "type": "kpi",
            "name": self.name,
            "value": val,
            "drill_ids": drill_ids,
            "font_size_title": self.font_size_title,
            "font_size_text": self.font_size_text,
            "font_color_text": self.font_color_text,
            "font_color_title": self.font_color_title,
            "bg_color": self.bg_color,
            "bg_color_header": self.bg_color_header,
            "text_align_header": self.text_align_header,
        }

    def get_text_data(self):
        self.ensure_one()

        return {
            "id": self.id,
            "type": "text",
            "name": self.name,
            "value": self.plain_text,
            "icon_size": self.icon_size,
            "font_size_title": self.font_size_title,
            "font_size_text": self.font_size_text,
            "font_color_text": self.font_color_text,
            "font_color_title": self.font_color_title,
            "bg_color": self.bg_color,
            "bg_color_header": self.bg_color_header,
            "text_align_header": self.text_align_header,
        }

    def get_table_data(self):
        self.ensure_one()

        # Reload the actual data of the query without recalculating the fields...
        self._refresh_query_result()

        tabledata = self.query_result and json.loads(self.query_result)["records"]

        tableHeight = 100
        margin = 35
        if int(self.font_size_title) > 0:
            margin = margin + int(self.font_size_title)
        if self.height > 1:
            tableHeight = (100 + (self.height - 1) * 110) - margin

        # get the group by, when more, this becomes a comma seperated list
        groupbyField = ",".join(
            [
                str(qryfield.name)
                for qryfield in self.query_key_ids.filtered(lambda x: x.is_group_by)
            ]
        )

        # build the column array
        tblColums = []
        for qryfield in self.query_key_ids:
            # Always add all columns, but hide them if not visible
            fieldsettings = {
                "title": qryfield.field_label,
                "field": qryfield.name,
                "hozAlign": qryfield.alignment,
                "visible": qryfield.is_visible,
                "download": qryfield.download,
            }
            if qryfield.field_layout_params:
                fieldsettings.update(json.loads(qryfield.field_layout_params))

            # Only if visible, set additional parameters
            if qryfield.is_visible:
                if qryfield.formatter:
                    fieldsettings["formatter"] = qryfield.formatter
                if qryfield.formatter_params:
                    fieldsettings["formatterParams"] = json.loads(qryfield.formatter_params)

                if qryfield.width:
                    fieldsettings["width"] = qryfield.width

                if qryfield.has_filter:
                    # if only the filter checkbox is ticked, set header_filter to True
                    if not qryfield.header_filter and not qryfield.header_filter_params:
                        fieldsettings["headerFilter"] = True
                    else:
                        # We have a more advanced filter
                        fieldsettings["headerFilter"] = qryfield.header_filter
                        fieldsettings["headerFilterParams"] = json.loads(
                            qryfield.header_filter_params
                        )
            tblColums.append(fieldsettings)

        return {
            "id": self.id,
            "type": "table",
            "name": self.name,
            "font_size_title": self.font_size_title,
            "font_color_title": self.font_color_title,
            "icon_size": self.icon_size,
            "bg_color": self.bg_color,
            "bg_color_header": self.bg_color_header,
            "text_align_header": self.text_align_header,
            "tabledata": tabledata,
            "tableHeight": tableHeight,
            "layout": "fitColumns",
            "columns": tblColums,
            "groupbyField": groupbyField,
            "dashboard_drill": self.xx_dashboard_drill,
            "model_id": self.model_id,
            "download_data": self.download_data,
            "pdf_orientation": self.pdf_orientation,
            "table_format_params": self.table_format_params
            and json.loads(self.table_format_params),
        }

    def get_dummy_data(self):
        self.ensure_one()
        return {"id": self.id, "type": "dummy", "name": self.name}

    def open_self_one2many(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Dashboard Tile",
            "view_type": "form",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "current",
        }  # pragma: no cover

    def unlink(self):
        """cascade unlink since ondelete=cascade does not clear ir.model.data needed for importing
        dashboards"""
        for tile in self:
            for field in tile.query_key_ids:
                field.unlink()
        return super().unlink()

    @staticmethod
    def calculate_relative_percentage(numbers, precision=2):
        total = sum(numbers)
        if total == 0:
            return [0] * len(
                numbers
            )  # Handle the case where the total is 0 to avoid division by zero
        return [round((x / total) * 100, 2) for x in numbers]


class DynDashboardQueryFields(models.Model):
    _name = "xx.dashboard.query.field"
    _order = "sequence, id"
    _description = "DynApps Dashboard Query Field"

    sequence = fields.Integer()
    name = fields.Char()
    dashboard_tile_id = fields.Many2one(comodel_name="xx.dashboard.tile")
    dashboard_tile_type = fields.Selection(related="dashboard_tile_id.display_type")

    is_visible = fields.Boolean(
        default=True, help="Uncheck to hide this column for this Grid field"
    )
    download = fields.Boolean(default=True, help="Uncheck to exclude from table download")
    field_label = fields.Text(
        help="Set the label shown in the column header (for table view) or as Axis-label for line"
    )
    download = fields.Boolean(default=True, help="Uncheck to exclude from table download")
    field_layout_params = fields.Text(help="Formatter config for the field")
    alignment = fields.Selection(
        selection=[("left", "Left"), ("center", "Center"), ("right", "Right")],
        default="left",
        help="Select the alignment of this field in the Grid view",
    )
    formatter = fields.Text(help="Formatter config for the Grid field")
    formatter_params = fields.Text(help="Formatter config for the Grid field")

    has_filter = fields.Boolean(default=True, help="Tick to show a filter on the Grid field")
    header_filter = fields.Text(
        help="Set to special filter field, leave blank for normal Grid filter"
    )
    header_filter_params = fields.Text(
        help="Set to config the special filter field, leave blank for normal Grid filter"
    )
    is_group_by = fields.Boolean(default=False, help="Tick to filter on this field")
    width = fields.Text(help="Set a fixed width in pixels, only numeric, for the Grid field")

    type_output = fields.Selection(
        selection=[("column", "Column"), ("line", "Line"), ("area", "Area")],
        default="column",
        help="Select the output type for this field, used in a Bar/Line/Mixed Chart",
    )
    show_on_axis = fields.Selection(
        selection=[("xaxis", "X-axis"), ("yaxis", "Y-axis"), ("legend", "Legend")],
        help="Select axis for this field",
    )
    opposite_axis_label = fields.Boolean(
        default=False, help="If yes, label is shown on the right side of the graph"
    )
    axis_label_color = fields.Char(
        default="", help="Set the colors of the Y-Axis info for this field"
    )

    def open_self_one2many(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Dashboard Query Field",
            "view_type": "form",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "current",
        }  # pragma: no cover
