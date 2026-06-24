from collections import defaultdict

from odoo import fields, models
from odoo.tools import SQL, format_date


class AccountAssetItReportHandler(models.AbstractModel):
    _name = "account.asset.it.report.handler"
    _inherit = ["account.report.custom.handler"]
    _description = "IT Assets Report Custom Handler"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        lines, totals_by_column_group = self._generate_report_lines(report, options)

        lines = self._group_lines_by_account(report, lines, options)

        total_columns = []
        for column_data in options["columns"]:
            col_value = totals_by_column_group[column_data["column_group_key"]].get(
                column_data["expression_label"]
            )
            col_value = col_value if column_data.get("figure_type") == "monetary" else ""
            total_columns.append(report._build_column_dict(col_value, column_data, options=options))

        if lines:
            lines.append(
                {
                    "id": report._get_generic_line_id(None, None, markup="total"),
                    "level": 1,
                    "name": self.env._("Total"),
                    "columns": total_columns,
                    "unfoldable": False,
                    "unfolded": False,
                }
            )

        return [(0, line) for line in lines]

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        column_group_options_map = report._split_options_per_column_group(options)

        for col in options["columns"]:
            column_group_options = column_group_options_map[col["column_group_key"]]
            if col["expression_label"] == "balance":
                col["name"] = ""
            if col["expression_label"] in ["assets_date_from", "depre_date_from"]:
                col["name"] = format_date(self.env, column_group_options["date"]["date_from"])
            elif col["expression_label"] in ["assets_date_to", "depre_date_to"]:
                col["name"] = format_date(self.env, column_group_options["date"]["date_to"])

        options["custom_columns_subheaders"] = [
            {"name": self.env._("Characteristics"), "colspan": 3},
            {"name": self.env._("Assets"), "colspan": 4},
            {"name": self.env._("Depreciation"), "colspan": 4},
            {"name": self.env._("Book Value"), "colspan": 1},
        ]
        return options

    def _generate_report_lines(self, report, options):
        column_names = [
            "assets_date_from",
            "assets_plus",
            "assets_minus",
            "assets_date_to",
            "depre_date_from",
            "depre_plus",
            "depre_minus",
            "depre_date_to",
            "balance",
        ]
        totals_by_column_group = defaultdict(lambda: dict.fromkeys(column_names, 0.0))
        all_lines_data = {}

        for column_group_key, column_group_options in report._split_options_per_column_group(
            options
        ).items():
            for row in self._query_values(column_group_options):
                asset_id = row["asset_id"]
                if asset_id not in all_lines_data:
                    all_lines_data[asset_id] = {
                        "asset_name": row["asset_name"],
                        "account_id": row["account_id"],
                        "col_groups": {},
                    }
                all_lines_data[asset_id]["col_groups"][column_group_key] = self._compute_columns(
                    column_group_options, row
                )

        lines = []
        column_expression = self.env["account.report.expression"]
        company_currency = self.env.company.currency_id

        for asset_id, data in all_lines_data.items():
            all_columns = []
            for column_data in options["columns"]:
                col_group_key = column_data["column_group_key"]
                expr_label = column_data["expression_label"]
                col_groups = data["col_groups"]
                if (
                    col_group_key not in col_groups or expr_label not in col_groups[col_group_key]
                ):  # pragma: no cover
                    all_columns.append(report._build_column_dict(None, None))
                    continue

                col_value = col_groups[col_group_key][expr_label]
                col_data = None if col_value is None else column_data
                all_columns.append(
                    report._build_column_dict(
                        col_value,
                        col_data,
                        options=options,
                        column_expression=column_expression,
                        currency=company_currency,
                    )
                )

                if column_data["figure_type"] == "monetary":
                    totals_by_column_group[col_group_key][expr_label] += col_value

            lines.append(
                {
                    "id": report._get_generic_line_id("asset.asset", asset_id),
                    "level": 2,
                    "name": data["asset_name"],
                    "columns": all_columns,
                    "unfoldable": False,
                    "unfolded": False,
                    "assets_account_id": data["account_id"],
                }
            )

        return lines, totals_by_column_group

    def _compute_columns(self, options, row):
        date_from = fields.Date.to_date(options["date"]["date_from"])
        date_to = fields.Date.to_date(options["date"]["date_to"])

        purchase_date = row["asset_purchase_date"]
        disposal_date = row["asset_disposal_date"]

        acquired_before = purchase_date and purchase_date < date_from
        disposed_in_period = disposal_date and date_from <= disposal_date <= date_to

        asset_opening = row["asset_purchase_amount"] if acquired_before else 0.0
        asset_opening += row["asset_in_before"]
        asset_opening -= row["asset_out_before"]

        asset_add = 0.0 if acquired_before else row["asset_purchase_amount"]
        asset_add += row["asset_in_during"]

        asset_minus = 0.0
        depre_opening = row["depreciated_before"]
        depre_add = row["depreciated_during"]
        depre_minus = 0.0

        asset_closing = asset_opening + asset_add - asset_minus
        depre_closing = depre_opening + depre_add - depre_minus

        if disposed_in_period:
            asset_minus = asset_closing
            depre_minus = depre_closing
            asset_closing = 0.0
            depre_closing = 0.0

        method = row["asset_method"] or ""
        percentage = row["asset_percentage"] or 0.0
        duration_rate = f"{percentage:.2f} %"

        return {
            "acquisition_date": (format_date(self.env, purchase_date) if purchase_date else ""),
            "method": method,
            "duration_rate": duration_rate,
            "assets_date_from": asset_opening,
            "assets_plus": asset_add,
            "assets_minus": asset_minus,
            "assets_date_to": asset_closing,
            "depre_date_from": depre_opening,
            "depre_plus": depre_add,
            "depre_minus": depre_minus,
            "depre_date_to": depre_closing,
            "balance": asset_closing - depre_closing,
        }

    def _query_values(self, options):
        company_ids = tuple(self.env["account.report"].get_report_company_ids(options))
        date_from = options["date"]["date_from"]
        date_to = options["date"]["date_to"]

        self.env["asset.asset"].check_access("read")
        self.env["asset.depreciation.line"].check_access("read")

        sql = SQL(
            """
            SELECT
                asset.id                                    AS asset_id,
                asset.name                                  AS asset_name,
                asset.purchase_date                         AS asset_purchase_date,
                asset.purchase_amount                       AS asset_purchase_amount,
                COALESCE(asset.sale_date, asset.dismiss_date)
                                                            AS asset_disposal_date,
                cat.asset_account_id                        AS account_id,
                MIN(mode.name)                              AS asset_method,
                MIN(dep.percentage)                         AS asset_percentage,
                COALESCE(SUM(dl.amount) FILTER (
                    WHERE dl.move_type = 'depreciated'
                      AND dl.date < %(date_from)s
                ), 0)                                       AS depreciated_before,
                COALESCE(SUM(dl.amount) FILTER (
                    WHERE dl.move_type = 'depreciated'
                      AND dl.date BETWEEN %(date_from)s AND %(date_to)s
                ), 0)                                       AS depreciated_during,
                COALESCE(SUM(dl.amount) FILTER (
                    WHERE dl.move_type = 'in'
                      AND dl.date < %(date_from)s
                ), 0)                                       AS asset_in_before,
                COALESCE(SUM(dl.amount) FILTER (
                    WHERE dl.move_type = 'in'
                      AND dl.date BETWEEN %(date_from)s AND %(date_to)s
                ), 0)                                       AS asset_in_during,
                COALESCE(SUM(dl.amount) FILTER (
                    WHERE dl.move_type IN ('out', 'loss')
                      AND dl.date < %(date_from)s
                ), 0)                                       AS asset_out_before
              FROM asset_asset           AS asset
              JOIN asset_category        AS cat  ON cat.id  = asset.category_id
              JOIN account_account       AS acc  ON acc.id  = cat.asset_account_id
              JOIN asset_depreciation    AS dep  ON dep.l10n_it_asset_id = asset.id
         LEFT JOIN asset_depreciation_mode AS mode ON mode.id = dep.mode_id
         LEFT JOIN asset_depreciation_line AS dl   ON dl.depreciation_id = dep.id
             WHERE asset.company_id IN %(company_ids)s
               AND asset.purchase_date <= %(date_to)s
               AND (
                     COALESCE(asset.sale_date, asset.dismiss_date) >= %(date_from)s
                     OR COALESCE(asset.sale_date, asset.dismiss_date) IS NULL
                   )
          GROUP BY asset.id, cat.asset_account_id
          ORDER BY cat.asset_account_id, asset.purchase_date, asset.id
            """,
            date_from=date_from,
            date_to=date_to,
            company_ids=company_ids,
        )

        self.env.cr.execute(sql)
        return self.env.cr.dictfetchall()

    def _group_lines_by_account(self, report, lines, options):
        if not lines:
            return lines

        line_vals_per_account_id = {}
        for line in lines:
            account_id = line.get("assets_account_id")
            model, res_id = report._get_model_info_from_id(line["id"])

            line["id"] = report._build_line_id(
                [
                    (None, "account.account", account_id),
                    (None, "asset.asset", res_id),
                ]
            )

            is_unfolded = any(
                report._get_model_info_from_id(uid) == ("account.account", account_id)
                for uid in options.get("unfolded_lines", [])
            )
            group = line_vals_per_account_id.setdefault(
                account_id,
                {
                    "id": report._build_line_id([(None, "account.account", account_id)]),
                    "columns": [],
                    "unfoldable": True,
                    "unfolded": is_unfolded or options.get("unfold_all"),
                    "level": 1,
                    "group_lines": [],
                },
            )
            group["group_lines"].append(line)

        rslt_lines = []
        idx_monetary = [
            i for i, col in enumerate(options["columns"]) if col["figure_type"] == "monetary"
        ]
        accounts = self.env["account.account"].browse(line_vals_per_account_id)

        for account in accounts:
            group = line_vals_per_account_id[account.id]
            group["name"] = f"{account.code} {account.name}"
            rslt_lines.append(group)

            group_totals = {i: 0.0 for i in idx_monetary}
            for child in group.pop("group_lines"):
                for i in idx_monetary:
                    group_totals[i] += child["columns"][i].get("no_format", 0)
                child["parent_id"] = group["id"]
                rslt_lines.append(child)

            for i, col_data in enumerate(options["columns"]):
                group["columns"].append(
                    report._build_column_dict(
                        group_totals.get(i, ""),
                        col_data,
                        options=options,
                    )
                )

        return rslt_lines
