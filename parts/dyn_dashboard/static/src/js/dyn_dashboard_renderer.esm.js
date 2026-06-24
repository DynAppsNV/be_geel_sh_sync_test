import {Component, onMounted, onWillUnmount, useRef, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {browser} from "@web/core/browser/browser";
import {localization} from "@web/core/l10n/localization";
import {renderToFragment} from "@web/core/utils/render";
import {router} from "@web/core/browser/router";
import {rpc} from "@web/core/network/rpc";
import {session} from "@web/session";
import {useService} from "@web/core/utils/hooks";

const {document, window} = globalThis;
export class DynDashboardRenderer extends Component {
    setup() {
        this.actionService = useService("action");
        // Checking for action data which could inform to re-direct to other odoo page.
        // This mechanism is employed as you can't pass a domain, context,..
        // to a tree,.. through URL
        const data_obj = JSON.parse(browser.localStorage.getItem("actionData"));
        if (data_obj) {
            browser.localStorage.removeItem("actionData");
            this._callAction(data_obj.data, "current", data_obj.view_type);
        }

        this.canvasRef = useRef("canvas");
        this.rpc = rpc;
        this.orm = useService("orm");
        this.router = router;
        // Date filter initializations
        var l_10n = localization;
        this.date_format = l_10n.dateFormat;
        this.datetime_format = l_10n.dateTimeFormat;
        // Adding date filter selection options in dictionary format : {'id':{'days':1,'text':"Text to show"}}
        this.dyn_date_selection_data = {
            l_none: _t("Date Filter"),
            l_day: _t("Today"),
            t_week: _t("This Week"),
            t_month: _t("This Month"),
            t_quarter: _t("This Quarter"),
            t_year: _t("This Year"),
            n_day: _t("Next Day"),
            n_week: _t("Next Week"),
            n_month: _t("Next Month"),
            n_quarter: _t("Next Quarter"),
            n_year: _t("Next Year"),
            ls_day: _t("Last Day"),
            ls_week: _t("Last Week"),
            ls_month: _t("Last Month"),
            ls_quarter: _t("Last Quarter"),
            ls_year: _t("Last Year"),
            l_week: _t("Last 7 days"),
            l_month: _t("Last 30 days"),
            l_quarter: _t("Last 90 days"),
            l_year: _t("Last 365 days"),
            ls_past_until_now: _t("Past Till Now"),
            ls_pastwithout_now: _t("Past Excluding Today"),
            n_future_starting_now: _t("Future Starting Now"),
            n_futurestarting_tomorrow: _t("Future Starting Tomorrow"),
            l_custom: _t("Custom Filter"),
        };
        this.dyn_date_selection_order = [
            "t_week",
            "t_month",
            "t_quarter",
            "t_year",
            "n_week",
            "n_month",
            "n_quarter",
            "n_year",
            "ls_week",
            "ls_month",
            "ls_quarter",
            "ls_year",
            "l_custom",
        ];
        this.state = useState({
            rowHeaderWidth: 0,
            dashboard_data: this.props.dashboard_data || {},
        });
        const state = this.state;
        this.dynCustomFilters = state.dashboard_data.custom_filters;
        this.dynCustomFilterChanged = false;
        this.dynDateFilterChanged = false;
        this.custom_date_do_rerender = false;
        this.dashboard_id_orig = state.dashboard_data.dashboard_id_orig;
        this.dashboard_id = state.dashboard_data.dashboard_id;
        this.date_filter_selection_orig = state.dashboard_data.date_filter_selection;
        this.dynDateFilterSelection = state.dashboard_data.date_filter_selection;
        this.date_filter_changed_orig = state.dashboard_data.date_filter_changed;
        this.dashboard_start_date_orig = state.dashboard_data.dashboard_start_date;
        this.dashboard_end_date_orig = state.dashboard_data.dashboard_end_date;
        this.dynDateFilterStartDate = state.dashboard_data.dashboard_start_date;
        this.dynDateFilterEndDate = state.dashboard_data.dashboard_end_date;
        this.dynOdooRecordID = state.dashboard_data.dashboard_id;
        // Check for hidden filters set in current session, this way when going back by breadcrump
        // the hidden filter is still activated. Hidden filters are by default not loaded
        // from user data
        this.filter_session_data =
            JSON.parse(browser.localStorage.getItem("filterData")) || {};
        if (this.filter_session_data) {
            for (const [key, value] of Object.entries(this.filter_session_data)) {
                let [dashboard_id, filter_id] = key.split("__");
                dashboard_id = parseInt(dashboard_id, 10);
                filter_id = parseInt(filter_id, 10);
                if (dashboard_id === this.dashboard_id) {
                    var select_field = "#selectbox_" + filter_id;
                    $(select_field).val(value).change();
                    const filter_values = {filter_id: filter_id, value: value};
                    this.assignToDynCustomFilters(filter_id, filter_values);
                }
            }
        }
        onMounted(() => {
            this._drawDynHeader();
            this._drawDynGrid();
        });
        onWillUnmount(() => {
            this.orm.call("xx.dashboard", "clear_filter_selections", [
                this.dashboard_id,
            ]);
        });
    }

    async _drawDynGrid() {
        var self = this;
        var dashboard_data = this.state.dashboard_data;
        if (!(self.dynCustomFilterChanged || self.dynDateFilterChanged)) {
            self._drawDynHeader();
        }

        if (this.grid) {
            // If the grid already exists : we removeAll tiles + destroy the grid
            // this combination makes a clean sheet, keeping the DOM ready to re-add the tiles
            // this scenario happens when:
            //      - after drill down - clicking on the breadcrumb to a previous Dashboard
            this.grid.removeAll(true);
            this.grid.destroy(false);
        }

        // eslint-disable-next-line no-undef
        var grid = GridStack.init({
            cellHeight: "110px",
            column: 24,
            disableResize: true,
            disableOneColumnMode: true,
            margin: 4,
            staticGrid: true,
        });

        for (const tile of dashboard_data.tiles) {
            grid.addWidget({
                w: tile.width,
                h: tile.height,
                content:
                    '<div id="dyn-tile-' +
                    tile.tile_id +
                    '" data-id="' +
                    tile.tile_id +
                    '" class="dyn-tile" />',
            });
        }

        self.grid = grid;

        for (const tile of dashboard_data.tiles) {
            self.rpc("/dyn_dashboard/get_tile_data", {
                tile_id: tile.tile_id,
                ctx: self.getContext(),
            }).then(function (data) {
                self.dynUpdateTileFormatting(data);
                dashboard_data.tile_data[tile.tile_id] = data;
                if (data.type === "line_chart") self._render_line_chart(data);
                else if (data.type === "pie_chart") self._render_line_chart(data);
                else if (data.type === "donut_chart") self._render_line_chart(data);
                else if (data.type === "radial_bar_chart")
                    self._render_line_chart(data);
                else if (data.type === "kpi") self._render_kpi.bind(self)(data);
                else if (data.type === "text") self._render_text(data);
                else if (data.type === "table") self._render_table(data);
                else if (data.type === "dummy") self._render_dummy(data);
            });
        }

        var windowResize = this._resizeGrid.bind(this);
        window.addEventListener("resize", function () {
            windowResize();
        });

        return true;
    }

    dynUpdateTileFormatting(data) {
        const pie_donut_perc = ["pie_chart", "donut_chart"].includes(data.type)
            ? "%"
            : "";
        if (!data.Error && data.options) {
            if (data.options.markers) {
                data.options.markers.formatter = function (val) {
                    return (
                        val &&
                        val.toLocaleString(data.locale, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                        }) + pie_donut_perc
                    );
                };
            }
            if (data.options.legend) {
                data.options.legend.formatter = function (val) {
                    return (
                        val &&
                        val.toLocaleString(data.locale, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                        })
                    );
                };
            }
            if (data.options.dataLabels) {
                data.options.dataLabels.formatter = function (val) {
                    return (
                        val &&
                        val.toLocaleString(data.locale, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                        }) + pie_donut_perc
                    );
                };
            }

            var labelsformat = {
                formatter: function (val) {
                    return (
                        val &&
                        val.toLocaleString(data.locale, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                        })
                    );
                },
            };
            if (data.options.xaxis) {
                data.options.xaxis.labels = labelsformat;
                if (data.options.yaxis) {
                    data.options.yaxis.labels = labelsformat;
                } else {
                    data.options.yaxis = {
                        labels: labelsformat,
                    };
                }
            }
            data.options.tooltip = {
                y: {
                    formatter: function (val) {
                        return (
                            val &&
                            val.toLocaleString(data.locale, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })
                        );
                    },
                },
            };
        }
    }

    _render_line_chart(data) {
        var self = this;
        var graph_html = renderToFragment("dyn_graph_template", {data: data});
        if (this.dynCustomFilterChanged || this.dynDateFilterChanged)
            $("#dyn-tile-" + data.id).empty();
        $("#dyn-tile-" + data.id).append(graph_html);

        $("#dyn-tile-" + data.id).css({"background-color": data.bg_color});
        $("#dyn-tile-" + data.id + " .dyn-header").css({
            "font-size": data.font_size_title + "px",
            "text-align": data.text_align_header,
            color: data.font_color_title,
            background: data.bg_color_header,
        });
        $("#dyn-tile-" + data.id + " .dyn-header .fa").css({
            "font-size": data.icon_size + "px",
            "text-align": "right",
            color: data.font_color_title,
        });

        // Make the containing tile 15px bigger, to have no scroll-bar and to fit the content nicely
        var height = data.options.chart.height + 15;
        $("#dyn-tile-" + data.id + " .dyn-graph-value").css({height: height + "px"});

        if (data.xx_dashboard_drill !== "") {
            data.options.chart.events = {
                // eslint-disable-next-line no-unused-vars
                dataPointSelection: function (event, chartContext, config) {
                    self._chartDrillAction(event);
                },
                // eslint-disable-next-line no-unused-vars
                click: function (event, chartContext, config) {
                    self._chartDrillAction(event);
                },
            };
        }

        // eslint-disable-next-line no-undef
        var chart = new ApexCharts(
            document.querySelector("#dyn-tile-" + data.id + " .dyn-graph-value"),
            data.options
        );
        chart.render();
    }

    _render_table(data) {
        var table_html = renderToFragment("dyn_table_template", {
            data: data,
            redrawOnParentResize: true,
        });

        if (this.dynCustomFilterChanged || this.dynDateFilterChanged)
            $("#dyn-tile-" + data.id).empty();
        $("#dyn-tile-" + data.id).append(table_html);

        $("#dyn-tile-" + data.id)
            .parent()
            .css({"background-color": data.bg_color});
        $("#dyn-tile-" + data.id + " .dyn-header").css({
            "font-size": data.font_size_title + "px",
            "text-align": data.text_align_header,
            color: data.font_color_title,
            background: data.bg_color_header,
        });
        $("#dyn-tile-" + data.id + " .dyn-header .fa").css({
            "font-size": data.icon_size + "px",
            "text-align": "right",
            color: data.font_color_title,
        });
        var nullToEmptyString = function (value) {
            // Return empty value for null.
            return value || "";
        };

        // eslint-disable-next-line no-undef
        var dashboard_table = new Tabulator(
            "#dyn-table-" + data.id,
            Object.assign(
                {
                    // Locale: produces errors
                    // locale: true,
                    height: data.tableHeight - (data.download_data ? 30 : 0),
                    data: data.tabledata,
                    layout: data.layout,
                    columns: data.columns.map((obj) => ({
                        ...obj,
                        accessorDownload: nullToEmptyString,
                    })),
                    groupBy: data.groupbyField,
                },
                data.table_format_params
            )
        );

        dashboard_table.on(
            "rowClick",
            function (e, row) {
                this._onTableDrillAction(e, row, data.id);
                e.stopPropagation();
            }.bind(this)
        );
        // TODO: set table fontsize if possible to data.font_size_text
        if (data.download_data) {
            // Trigger download of data.csv file
            document
                .getElementById("btn-download-csv-" + data.id)
                .addEventListener("click", function () {
                    dashboard_table.download("csv", "data.csv");
                });

            // Trigger download of data.json file
            document
                .getElementById("btn-download-json-" + data.id)
                .addEventListener("click", function () {
                    dashboard_table.download("json", "data.json");
                });

            // Trigger download of data.xlsx file
            document
                .getElementById("btn-download-xlsx-" + data.id)
                .addEventListener("click", function () {
                    dashboard_table.download("xlsx", "data.xlsx", {
                        sheetName: "My Data",
                    });
                });

            // Trigger download of data.pdf file
            document
                .getElementById("btn-download-pdf-" + data.id)
                .addEventListener("click", function () {
                    dashboard_table.download("pdf", "data.pdf", {
                        orientation: data.pdf_orientation,
                        title: data.name,
                    });
                });
        }
    }

    _render_dummy(data) {
        var dummy_html = renderToFragment("dyn_dummy_template", {
            data: data,
        });
        if (this.dynCustomFilterChanged || this.dynDateFilterChanged)
            $("#dyn-tile-" + data.id).empty();
        $("#dyn-tile-" + data.id).append(dummy_html);
        $("#dyn-tile-" + data.id).css({"background-color": "#DDD"});
    }

    // No numbers, just plain text and styling : config in the dashboard.py file
    _render_text(data) {
        var text_html = renderToFragment("dyn_text_template", {
            data: data,
        });
        if (this.dynCustomFilterChanged || this.dynDateFilterChanged)
            $("#dyn-tile-" + data.id).empty();
        $("#dyn-tile-" + data.id).append(text_html);

        $("#dyn-tile-" + data.id)
            .find(".dashboard_drill_action")
            .off("click")
            .on("click", this._onKpiDrillAction.bind(this));
        $("#dyn-tile-" + data.id).css({"background-color": data.bg_color});
        $("#dyn-tile-" + data.id + " .dyn-header").css({
            "font-size": data.font_size_title + "px",
            "text-align": data.text_align_header,
            color: data.font_color_title,
            background: data.bg_color_header,
        });
        $("#dyn-tile-" + data.id + " .dyn-header .fa").css({
            "font-size": data.icon_size + "px",
            "text-align": "right",
            color: data.font_color_title,
        });
        $("#dyn-tile-" + data.id + " .dyn-text-value").css({
            "font-size": data.font_size_text + "px",
            color: data.font_color_text,
        });
    }

    // KPI : expects only a number
    _render_kpi(data) {
        const self = this;
        var kpi_html = renderToFragment("dyn_kpi_template", {
            data: data,
        });
        if (this.dynCustomFilterChanged || this.dynDateFilterChanged)
            $("#dyn-tile-" + data.id).empty();
        $("#dyn-tile-" + data.id).append(kpi_html);
        // Adding events
        $("#dyn-tile-" + data.id)
            .find(".dashboard_drill_action")
            .off("click")
            .on("click", this._onKpiDrillAction.bind(self));

        $("#dyn-tile-" + data.id).css({"background-color": data.bg_color});
        $("#dyn-tile-" + data.id + " .dyn-header").css({
            "font-size": data.font_size_title + "px",
            "text-align": data.text_align_header,
            color: data.font_color_title,
            background: data.bg_color_header,
        });
        $("#dyn-tile-" + data.id + " .dyn-header .fa").css({
            "font-size": data.icon_size + "px",
            "text-align": "right",
            color: data.font_color_title,
        });
        $("#dyn-tile-" + data.id + " .dyn-kpi-value").css({
            "font-size": data.font_size_text + "px",
            color: data.font_color_text,
        });
    }

    async _drawDynHeader() {
        var self = this;
        if (!this.header) {
            var data = self.props.dashboard_data;
            var header_html = renderToFragment("dyn_dashboard_header", {
                dyn_dashboard_name: data.name,
                data_custom_filters: data.custom_filters,
                date_selection_data: self.dyn_date_selection_data,
                date_selection_order: self.dyn_date_selection_order,
            });
            $("#dyn-custom-filters").removeClass("dyn_hide");
            $("#dyn-custom-filters").append(header_html);
            this.header = header_html;
            if (data.show_date_filter) {
                $(".dyn_datefilter_dropdown").removeClass("dyn_hide");
                self.dynDateFilterSelection = data.date_filter_selection;
                if (self.dynDateFilterSelection) {
                    $("#" + self.dynDateFilterSelection).addClass(
                        "dyn_date_filter_selected"
                    );
                    $("#dyn_date_filter_selection").text(
                        self.dyn_date_selection_data[self.dynDateFilterSelection]
                    );
                }
            }
            // Custom Date Filter
            var startDate = self.state.dashboard_data.dashboard_start_date
                ? moment.utc(self.state.dashboard_data.dashboard_start_date).local()
                : moment();
            var endDate = self.state.dashboard_data.dashboard_end_date
                ? moment.utc(self.state.dashboard_data.dashboard_end_date).local()
                : moment();
            if (self.state.dashboard_data.dashboard_start_date) {
                // Causing automatic re-render when selecting "custom" in date filter menu
                self.custom_date_immediate_rerender = true;
            }
            $("#date-range-picker").daterangepicker({
                opens: "left",
                locale: {
                    format: "DD-MM-YYYY",
                },
                startDate: startDate,
                endDate: endDate,
            });
            $("#date-range-picker").on(
                "apply.daterangepicker",
                self._ApplyCustomDateFilter.bind(self)
            );
            if (data.show_custom_date_filter) {
                $("#date-range-picker_div").removeClass("dyn_hide");
            }

            // Custom filters dropdown
            data.custom_filters.forEach(function (custom_filter) {
                if (custom_filter.selection) {
                    var select_field = "#selectbox_" + custom_filter.filter_id;
                    var context = JSON.stringify(self.getContext());
                    $(select_field)
                        .select2({
                            allowClear: true,
                            ajax: {
                                url: "/dyn_dashboard/get_filter_data",
                                dataType: "json",
                                headers: {
                                    "Content-Type": "application/json",
                                    "X-CSRF-TOKEN": $('meta[name="csrf-token"]').attr(
                                        "content"
                                    ),
                                },
                                delay: 250,
                                params: {
                                    page: 1,
                                },
                                data: function (term, page) {
                                    return {
                                        q: term,
                                        page: page || 1,
                                        filter_id: custom_filter.filter_id,
                                        context_to_pass: context,
                                    };
                                },
                                results: function (filter_data) {
                                    return {
                                        results: filter_data.results,
                                        more: filter_data.more,
                                    };
                                },
                                cache: true,
                            },
                            initSelection: function (element, callback) {
                                var values = $(element).val().split(",");
                                self.get_initselection_data(
                                    values,
                                    custom_filter.filter_id
                                ).then(function (selectiondata) {
                                    callback(
                                        custom_filter.multiselect
                                            ? selectiondata
                                            : selectiondata[0]
                                    );
                                });
                            },
                            theme: "classic",
                            minimumResultsForSearch: 10,
                            placeholder: custom_filter.name,
                            overflow: "hidden",
                            multiple: custom_filter.multiselect,
                            height: "auto",
                            dropdownAutoWidth: true,
                        })
                        .on("change", function () {
                            var customfilter_id = custom_filter.filter_id;
                            var filter_values = {
                                filter_id: customfilter_id,
                                value: $(this).select2("val"),
                            };
                            self.assignToDynCustomFilters(
                                customfilter_id,
                                filter_values
                            );
                        });
                    $(select_field).val(custom_filter.value).trigger("change");
                }
                if (custom_filter.hidden) {
                    $(select_field).addClass("dyn_hide");
                }
                $(".apply-custom-filter").removeClass("dyn_hide");
            });
            $(".apply-custom-filter").on("click", self._ApplyCustomFilter.bind(self));
            $(".dropdown-menu").on("click", self._dynOnDateFilterMenuSelect.bind(self));
        }
    }

    async assignToDynCustomFilters(customfilter_id, filter_values) {
        var objIndex = Array.isArray(this.dynCustomFilters)
            ? this.dynCustomFilters.findIndex(
                  (obj) => obj.filter_id === customfilter_id
              )
            : -1;
        if (objIndex > -1) {
            this.dynCustomFilters[objIndex].value = filter_values.value;
        } else {
            this.dynCustomFilters.push(filter_values);
        }
    }

    // Event handler methods
    async _ApplyCustomFilter() {
        var self = this;

        $(".custom_filter").each(function () {
            if (this.type === "text") {
                var custom_filter_id = Number(this.id);
                var i = self.dynCustomFilters.findIndex(
                    (obj) => obj.filter_id === custom_filter_id
                );
                if (i > -1) {
                    self.dynCustomFilters[i].value = this.value;
                } else {
                    self.dynCustomFilters.push({
                        filter_id: custom_filter_id,
                        value: this.value,
                    });
                }
            }
        });
        self.dynCustomFilterChanged = true;

        await this.orm.call("xx.dyn.custom.filter.value", "update_values", [[], {}], {
            context: self.getContext(),
        });
        self.dyn_fetch_items_data().then(function () {
            self.dynUpdateDashboardItem(
                Object.keys(self.state.dashboard_data.tile_data)
            );
        });
    }

    _dynOnDateFilterMenuSelect(e) {
        if (e.target.id !== "date_filter_menu") {
            var self = this;
            $(".dyn_date_filter_selected").each(function () {
                $(this).removeClass("dyn_date_filter_selected");
            });
            $(e.target.parentElement).addClass("dyn_date_filter_selected");
            $("#dyn_date_filter_selection").text(
                self.dyn_date_selection_data[e.target.parentElement.id]
            );

            if (e.target.parentElement.id !== "l_custom") {
                $("#date-range-picker_div").addClass("dyn_hide");
                if (e.target.parentElement.id === "l_none") {
                    self._onClearDateValues();
                } else {
                    self._dynOnApplyDateFilter();
                }
            } else if (e.target.parentElement.id === "l_custom") {
                $("#date-range-picker_div").removeClass("dyn_hide");
                // When custom date has been set before, already re-render
                if (self.custom_date_do_rerender) {
                    $("#date-range-picker")
                        .data("daterangepicker")
                        .element.trigger(
                            "apply.daterangepicker",
                            $("#date-range-picker").data("daterangepicker")
                        );
                }
            }
        }
    }

    _ApplyCustomDateFilter(ev, picker) {
        // Selection of daterange by daterangepicker
        var self = this;
        self.custom_date_do_rerender = true;
        self.dynDateFilterChanged = true;
        var start_date = picker.startDate;
        var end_date = picker.endDate;
        self.dynDateFilterStartDate = start_date;
        self.dynDateFilterEndDate = end_date;

        // Adjusting the start and end dates based on the timezone offset
        self.dynDateFilterSelection = $(".dyn_date_filter_selected").attr("id");

        self.dyn_fetch_items_data().then(function () {
            self.dynUpdateDashboardItem(
                Object.keys(self.state.dashboard_data.tile_data)
            );
        });
    }

    _dynOnApplyDateFilter() {
        var self = this;
        self.dynDateFilterSelection = $(".dyn_date_filter_selected").attr("id");
        self.dynDateFilterChanged = true;
        self.dyn_fetch_items_data().then(function () {
            self.dynUpdateDashboardItem(
                Object.keys(self.state.dashboard_data.tile_data)
            );
        });
    }

    _onClearDateValues() {
        var self = this;
        self.dynDateFilterSelection = "l_none";
        self.dynDateFilterStartDate = false;
        self.dynDateFilterEndDate = false;

        $.when(self.dyn_fetch_items_data()).then(function () {
            self.dynUpdateDashboardItem(
                Object.keys(self.state.dashboard_data.tile_data)
            );
        });
    }

    dyn_fetch_items_data() {
        var self = this;
        var items_promises = [];
        self.state.dashboard_data.tile_ids.forEach(function (value) {
            items_promises.push(
                self.orm
                    .call(
                        "xx.dashboard",
                        "dyn_fetch_item",
                        [[value], self.dashboard_id],
                        {
                            context: self.getContext(),
                        }
                    )
                    .then(function (result) {
                        self.state.dashboard_data.tile_data[value] = result[value];
                    })
            );
        });
        return Promise.all(items_promises);
    }

    on_detach_callback() {
        this.dynCustomFilterChanged = false;
        this.dynDateFilterChanged = false;
        this.dashboard_id_orig = this.dashboard_id;
        this._super.apply(this, arguments);
    }

    _callAction(data, target = "current", viewType = "list") {
        if (target === "current") {
            var views = [
                [false, "list"],
                [false, "form"],
            ];
            if (viewType === "form") {
                views = [[false, "form"]];
            }
            var self = this;
            var action = {
                name: _t(data.model_name),
                type: "ir.actions.act_window",
                res_model: data.model_model,
                views: data.views || views,
                target: "current",
                additionalContext: {on_reverse_breadcrumb: self.on_reverse_breadcrumb},
            };
            if (data.drill_ids) {
                action.domain = [["id", "in", data.drill_ids]];
            }
            if (data.context) {
                action.context = data.context;
            }
            if (data.view_type) {
                action.view_type = data.view_type;
            }
            if (data.res_id) {
                action.res_id = data.res_id;
            }
            self.actionService.doAction(action);
        } else {
            // Opening a new tab and keeping data in localStorage so the new tab can redirect
            // This mechanism is employed as you can't pass a domain, context,..
            // to a tree,.. through URL
            const actionDataNewTab = {
                model_name: data.model_name,
                model_model: data.model_model,
                drill_ids: data.drill_ids,
                context: data.context,
                views: data.views,
            };
            browser.localStorage.setItem(
                "actionData",
                JSON.stringify({
                    data: actionDataNewTab,
                    view_type: viewType,
                })
            );
            window.open(window.location.href, "_blank");
        }
    }

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    /* eslint-disable radix */
    _onKpiDrillAction(event) {
        var self = this;
        event.stopPropagation();

        // Extract the ID of the tile
        var tile_id = parseInt(event.target.dataset.id);
        self._drillAction(tile_id);
    }

    _chartDrillAction(event) {
        var self = this;

        if (event) {
            event.stopPropagation();

            // Extract the ID of the tile
            var tile_id = parseInt(
                event.target.closest('div[id^="dyn-tile"]').dataset.id
            );
            self._drillAction(tile_id);
        }
    }

    /* eslint-enable radix */

    _onTableDrillAction(event, row, tile_id) {
        var self = this;
        if ("ids" in row._row.data) {
            var tile_data = self.state.dashboard_data.tile_data[tile_id];
            tile_data.drill_ids = row._row.data.ids.split(",");
            const target = tile_data.new_tab ? "new" : "current";
            self._callAction(tile_data, target);
        } else {
            this.rpc("/dyn_dashboard/get_table_drill_data", {
                tile_id: tile_id,
                row_id: row._row.data.id || 0,
                res_model: row._row.data.res_model || "",
                ctx: self.getContext(),
            }).then(function (data) {
                const target = data.new_tab ? "new" : "current";
                var context_to_pass = self.getContext();
                context_to_pass.date_filter_changed_orig = self.dynDateFilterChanged;

                if (data.drill_type === "dashboard" && data.xx_dashboard_action) {
                    context_to_pass.dashboard_id =
                        data.xx_dashboard_action.context.dashboard_id;
                    const data_for_call = {
                        model_name: data.xx_dashboard_action.name,
                        model_model: "xx.dashboard",
                        context: context_to_pass,
                        views: [[false, "dyn_dashboard"]],
                    };

                    self._callAction(data_for_call, target, null);
                } else if (
                    data.drill_type === "model" &&
                    data.model_name &&
                    data.model_model
                ) {
                    var name = _t(data.model_name);
                    var action = {};
                    if (data.new_tab) {
                        // Generate url for a single id
                        var drill_url = `web#id=${data.target_id}&model=${data.model_model}&view_type=form`;
                        action = {
                            type: "ir.actions.act_url",
                            name: name,
                            target: "new",
                            url: drill_url,
                        };
                        self.actionService.doAction(action);
                    } else {
                        const data_for_call = {
                            model_name: name,
                            model_model: data.model_model,
                            view_mode: "form,list",
                            drill_ids: [data.target_id],
                            res_id: data.target_id,
                        };
                        self._callAction(data_for_call, "current", "form");
                    }
                } else if (data.drill_type === "filter" && data.filter_drill) {
                    self._addFilterToSession(data);
                    self._applyHiddenFilter(data);
                }
            });
        }
    }

    _applyHiddenFilter(data) {
        var select_field = "#selectbox_" + data.filter_drill;
        $(select_field).val(data.target_id).change();
        this._ApplyCustomFilter();
    }

    _addFilterToSession(data) {
        this.filter_session_data[this.dashboard_id + "__" + data.filter_drill] =
            data.target_id;
        browser.localStorage.setItem(
            "filterData",
            JSON.stringify(this.filter_session_data)
        );
    }

    on_reverse_breadcrumb() {
        this.router.pushState({});
    }

    _drillAction(tile_id) {
        var self = this;

        var data = self.state.dashboard_data.tile_data[tile_id];
        const target = data.new_tab ? "new" : "current";
        if (data.drill_type === "dashboard" && data.xx_dashboard_action) {
            self.dashboard_id_orig = self.dashboard_id;
            const context_to_pass = self.getContext();
            context_to_pass.dashboard_id =
                data.xx_dashboard_action.context.dashboard_id;
            const data_for_call = {
                model_name: data.xx_dashboard_action.name,
                model_model: "xx.dashboard",
                context: context_to_pass,
                views: [[false, "dyn_dashboard"]],
            };
            self._callAction(data_for_call, target, null);
        } else if (
            data.drill_type === "model" &&
            data.model_name &&
            data.model_model &&
            data.drill_ids
        ) {
            // Open tree view
            self._callAction(data, target, "list");
        } else if (data.res_model_field && data.res_id_field) {
            // Open form view
            self._callAction(data, target, "form");
        } else if (data.drill_type === "filter" && data.filter_drill) {
            const data_load = {
                filter_drill: data.filter_drill,
                target_id: data.drill_ids[0],
            };
            self._addFilterToSession(data_load);
            self._applyHiddenFilter(data_load);
        }
    }

    get_initselection_data(values, filter_id) {
        var self = this;
        var items_promises = [];
        for (const id of values) {
            if (id !== "") {
                items_promises.push(
                    self
                        .rpc("/dyn_dashboard/get_init_selection", {
                            filter_id: filter_id,
                            search_value: id,
                            context_to_pass: JSON.stringify(self.getContext()),
                        })
                        .then(function (result) {
                            return result;
                        })
                );
            }
        }
        return Promise.all(items_promises);
    }

    _resizeGrid() {
        const width = document.body.clientWidth;

        // Only on the dashboard-view we make the control_panel a little less high
        $(".o_cp_left").parent().hide();
        $(".o_cp_bottom").hide();

        if (width < 700) {
            this.grid.column(1, "none");
        } else {
            this.grid.column(24, "none");
        }
    }

    on_attach_callback() {
        var self = this;
        self._super.apply(self, arguments);

        self._drawDynGrid();
        self._resizeGrid();
    }

    dynUpdateDashboardItem(ids) {
        var self = this;
        for (var i = 0; i < ids.length; i++) {
            var data = self.state.dashboard_data.tile_data[ids[i]];
            self.dynUpdateTileFormatting(data);
            if (data.type === "line_chart") self._render_line_chart(data);
            else if (data.type === "pie_chart") self._render_line_chart(data);
            else if (data.type === "donut_chart") self._render_line_chart(data);
            else if (data.type === "radial_bar_chart") self._render_line_chart(data);
            else if (data.type === "kpi") self._render_kpi(data);
            else if (data.type === "text") self._render_text(data);
            else if (data.type === "table") self._render_table(data);
            else if (data.type === "dummy") self._render_dummy(data);
        }
    }

    getContext() {
        var self = this;
        var context = {
            dynDateFilterSelection: self.dynDateFilterSelection,
            dynDateFilterStartDate: self.dynDateFilterStartDate
                ? moment.utc(self.dynDateFilterStartDate).local()
                : false,
            dynDateFilterEndDate: self.dynDateFilterEndDate
                ? moment.utc(self.dynDateFilterEndDate).local()
                : false,
            dynCustomFilters: self.dynCustomFilters,
            dynCustomFilterChanged: self.dynCustomFilterChanged,
            dynDateFilterChanged: self.dynDateFilterChanged,
            dashboard_id_orig: self.dashboard_id_orig,
            date_filter_selection_orig: self.dynDateFilterSelection,
            dashboard_start_date_orig: self.dashboard_start_date_orig,
            dashboard_end_date_orig: self.dashboard_end_date_orig,
            odoo_record_id: self.dynOdooRecordID,
            dynOdooRecordID: self.dynOdooRecordID,
            allowed_company_ids: self.env.searchModel.context.allowed_company_ids,
        };
        return Object.assign(context, session.user_context);
    }
}

DynDashboardRenderer.template = "dyn_dashboard.Renderer";
