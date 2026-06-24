# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

import odoo.http as http
from odoo.http import request


class DiagramView(http.Controller):
    @http.route("/dyn_dashboard/get_dashboard_data", type="jsonrpc", auth="user")
    def get_dashboard_data(self, dashboard_id, context_to_pass):  # pragma: no cover
        dashboard = request.env["xx.dashboard"].browse(dashboard_id)
        dashboard_data = dashboard.with_context(**context_to_pass).fetch_dashboard_data(
            dashboard_id
        )
        return dashboard_data

    @http.route("/dyn_dashboard/get_tile_data", type="jsonrpc", auth="user")
    def get_dashboard_tile(self, tile_id, ctx):
        tile = request.env["xx.dashboard.tile"].browse(tile_id)
        return tile.with_context(**ctx).get_data()

    @http.route("/dyn_dashboard/get_table_drill_data", type="jsonrpc", auth="user")
    def get_dashboard_table_drill(self, tile_id, row_id, res_model, ctx):
        tile = request.env["xx.dashboard.tile"].browse(tile_id)
        return tile.with_context(**ctx).get_row_data_drill_action(row_id, res_model)

    @http.route(
        "/dyn_dashboard/get_filter_data",
        methods=["GET", "POST"],
        type="http",
        auth="public",
        website=True,
    )
    def get_filter_data(self, **kwargs):
        q = kwargs.get("q", "")
        page = kwargs.get("page", 1)
        filter_id = kwargs.get("filter_id")
        context_to_pass = kwargs.get("context_to_pass")
        ctx = json.loads(context_to_pass)
        res = (
            request.env["xx.dyn.custom.filter"]
            .browse(int(filter_id))
            .with_context(**ctx)
            .get_filter_selections(int(page), q)
        )
        return json.dumps(res)

    @http.route("/dyn_dashboard/get_init_selection", type="jsonrpc", auth="user")
    def get_init_selection(self, filter_id, search_value, context_to_pass):  # pragma: no cover
        ctx = json.loads(context_to_pass)
        return (
            request.env["xx.dyn.custom.filter"]
            .browse(int(filter_id))
            .with_context(**ctx)
            .get_selection_values(search_value)
        )
