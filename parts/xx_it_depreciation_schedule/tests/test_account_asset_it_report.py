from datetime import date

from odoo.fields import Command

from odoo.addons.l10n_it_asset_management.tests.common import Common


class TestAccountAssetItReport(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.handler = cls.env["account.asset.it.report.handler"]
        # Create a second account/category for grouping tests
        cls.asset_fixed_account_2 = cls.env["account.account"].create(
            {
                "name": "Fixed Assets 2",
                "code": "TFA2",
                "account_type": "asset_fixed",
            }
        )
        cls.asset_category_2 = cls.env["asset.category"].create(
            {
                "name": "Asset category 2",
                "asset_account_id": cls.asset_fixed_account_2.id,
                "depreciation_account_id": cls.expense_account.id,
                "fund_account_id": cls.asset_non_current_account.id,
                "gain_account_id": cls.income_account.id,
                "journal_id": cls.general_journal.id,
                "loss_account_id": cls.expense_account.id,
                "type_ids": [
                    Command.create(
                        {
                            "depreciation_type_id": cls.civilistico_asset_dep_type.id,
                            "mode_id": cls.materiale_asset_dep_mode.id,
                        }
                    )
                ],
            }
        )

    def _make_options(self, date_from, date_to):
        return {
            "date": {
                "date_from": str(date_from),
                "date_to": str(date_to),
            },
            "companies": [{"id": self.env.company.id}],
        }

    def _add_depreciation_lines(self, asset, lines):
        """Add raw depreciation lines directly to the first depreciation record."""
        dep = asset.depreciation_ids[:1]
        dep.line_ids = [Command.clear()] + [Command.create(ln) for ln in lines]

    # --- _compute_columns unit tests ---

    def test_compute_columns_acquired_before(self):
        row = {
            "asset_purchase_date": date(2023, 6, 1),
            "asset_purchase_amount": 1000.0,
            "asset_disposal_date": None,
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 0.0,
            "depreciated_before": 200.0,
            "depreciated_during": 100.0,
            "asset_method": "Straight-line",
            "asset_percentage": 10.0,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)

        self.assertEqual(cols["assets_date_from"], 1000.0)
        self.assertEqual(cols["assets_plus"], 0.0)
        self.assertEqual(cols["assets_minus"], 0.0)
        self.assertEqual(cols["assets_date_to"], 1000.0)
        self.assertEqual(cols["depre_date_from"], 200.0)
        self.assertEqual(cols["depre_plus"], 100.0)
        self.assertEqual(cols["depre_minus"], 0.0)
        self.assertEqual(cols["depre_date_to"], 300.0)
        self.assertEqual(cols["balance"], 700.0)

    def test_compute_columns_acquired_in_period(self):
        row = {
            "asset_purchase_date": date(2024, 3, 1),
            "asset_purchase_amount": 500.0,
            "asset_disposal_date": None,
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 0.0,
            "depreciated_before": 0.0,
            "depreciated_during": 50.0,
            "asset_method": "Degressive",
            "asset_percentage": 20.0,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)

        self.assertEqual(cols["assets_date_from"], 0.0)
        self.assertEqual(cols["assets_plus"], 500.0)
        self.assertEqual(cols["assets_date_to"], 500.0)
        self.assertEqual(cols["depre_date_from"], 0.0)
        self.assertEqual(cols["depre_plus"], 50.0)
        self.assertEqual(cols["balance"], 450.0)

    def test_compute_columns_disposed_in_period(self):
        row = {
            "asset_purchase_date": date(2022, 1, 1),
            "asset_purchase_amount": 800.0,
            "asset_disposal_date": date(2024, 6, 30),
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 0.0,
            "depreciated_before": 400.0,
            "depreciated_during": 0.0,
            "asset_method": "Straight-line",
            "asset_percentage": 25.0,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)

        self.assertEqual(cols["assets_minus"], 800.0)
        self.assertEqual(cols["assets_date_to"], 0.0)
        self.assertEqual(cols["depre_minus"], 400.0)
        self.assertEqual(cols["depre_date_to"], 0.0)
        self.assertEqual(cols["balance"], 0.0)

    def test_compute_columns_no_method(self):
        row = {
            "asset_purchase_date": date(2024, 1, 1),
            "asset_purchase_amount": 100.0,
            "asset_disposal_date": None,
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 0.0,
            "depreciated_before": 0.0,
            "depreciated_during": 0.0,
            "asset_method": None,
            "asset_percentage": None,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)

        self.assertEqual(cols["method"], "")
        self.assertEqual(cols["duration_rate"], "0.00 %")

    # --- _query_values integration tests ---

    def test_empty_report(self):
        options = self._make_options(date(2030, 1, 1), date(2030, 12, 31))
        rows = self.handler._query_values(options)
        self.assertIsInstance(rows, list)

    def test_query_asset_acquired_before_period(self):
        asset = self._create_asset(asset_date=date(2023, 6, 1))
        self._add_depreciation_lines(
            asset,
            [
                {
                    "name": "2023 dep",
                    "date": date(2023, 12, 31),
                    "move_type": "depreciated",
                    "amount": 100.0,
                },
                {
                    "name": "2024 dep",
                    "date": date(2024, 12, 31),
                    "move_type": "depreciated",
                    "amount": 100.0,
                },
            ],
        )
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        rows = self.handler._query_values(options)
        row = next((r for r in rows if r["asset_id"] == asset.id), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["depreciated_before"], 100.0)
        self.assertEqual(row["depreciated_during"], 100.0)

    def test_query_asset_acquired_in_period(self):
        asset = self._create_asset(asset_date=date(2024, 3, 15))
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        rows = self.handler._query_values(options)
        row = next((r for r in rows if r["asset_id"] == asset.id), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["asset_purchase_amount"], 1000.0)
        self.assertEqual(row["depreciated_before"], 0.0)

    def test_query_asset_disposed_in_period(self):
        asset = self.env["asset.asset"].create(
            {
                "name": "Disposed asset",
                "category_id": self.asset_category_1.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
                "purchase_amount": 1000.0,
                "purchase_date": date(2023, 1, 1),
                "dismiss_date": date(2024, 6, 30),
            }
        )
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        rows = self.handler._query_values(options)
        row = next((r for r in rows if r["asset_id"] == asset.id), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["asset_disposal_date"], date(2024, 6, 30))

    def test_query_excludes_future_assets(self):
        asset = self._create_asset(asset_date=date(2025, 1, 1))
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        rows = self.handler._query_values(options)
        asset_ids = [r["asset_id"] for r in rows]
        self.assertNotIn(asset.id, asset_ids)

    def test_query_grouping_by_account(self):
        asset1 = self._create_asset(asset_date=date(2024, 1, 1))
        asset2 = self.env["asset.asset"].create(
            {
                "name": "Asset cat2",
                "category_id": self.asset_category_2.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
                "purchase_amount": 500.0,
                "purchase_date": date(2024, 1, 1),
            }
        )
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        rows = self.handler._query_values(options)
        account_ids = {r["account_id"] for r in rows}
        self.assertIn(asset1.category_id.asset_account_id.id, account_ids)
        self.assertIn(asset2.category_id.asset_account_id.id, account_ids)

    def test_report_action_accessible(self):
        action = self.env.ref("xx_it_depreciation_schedule.action_account_report_it_assets")
        self.assertTrue(action)
        self.assertEqual(action.tag, "account_report")

    # --- _compute_columns additional edge cases ---

    def test_compute_columns_in_before_and_out_before(self):
        """asset_in_before and asset_out_before are included in the opening balance."""
        row = {
            "asset_purchase_date": date(2022, 1, 1),
            "asset_purchase_amount": 1000.0,
            "asset_disposal_date": None,
            "asset_in_before": 200.0,
            "asset_out_before": 50.0,
            "asset_in_during": 0.0,
            "depreciated_before": 0.0,
            "depreciated_during": 0.0,
            "asset_method": None,
            "asset_percentage": None,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)
        # acquired_before=True: opening = purchase_amount + in_before - out_before
        self.assertEqual(cols["assets_date_from"], 1150.0)
        self.assertEqual(cols["assets_date_to"], 1150.0)

    def test_compute_columns_in_during(self):
        """asset_in_during is included in assets_plus for assets acquired in the period."""
        row = {
            "asset_purchase_date": date(2024, 3, 1),
            "asset_purchase_amount": 500.0,
            "asset_disposal_date": None,
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 100.0,
            "depreciated_before": 0.0,
            "depreciated_during": 0.0,
            "asset_method": None,
            "asset_percentage": None,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)
        self.assertEqual(cols["assets_plus"], 600.0)
        self.assertEqual(cols["assets_date_to"], 600.0)

    def test_compute_columns_disposal_before_period(self):
        """Disposal date before period start does not zero out the asset."""
        row = {
            "asset_purchase_date": date(2022, 1, 1),
            "asset_purchase_amount": 1000.0,
            "asset_disposal_date": date(2023, 12, 31),
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 0.0,
            "depreciated_before": 500.0,
            "depreciated_during": 0.0,
            "asset_method": None,
            "asset_percentage": None,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)
        self.assertEqual(cols["assets_minus"], 0.0)
        self.assertEqual(cols["depre_minus"], 0.0)
        self.assertEqual(cols["assets_date_to"], 1000.0)

    def test_compute_columns_disposal_after_period(self):
        """Disposal date after period end does not zero out the asset."""
        row = {
            "asset_purchase_date": date(2022, 1, 1),
            "asset_purchase_amount": 1000.0,
            "asset_disposal_date": date(2025, 3, 1),
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 0.0,
            "depreciated_before": 300.0,
            "depreciated_during": 100.0,
            "asset_method": None,
            "asset_percentage": None,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)
        self.assertEqual(cols["assets_minus"], 0.0)
        self.assertEqual(cols["depre_minus"], 0.0)

    def test_compute_columns_no_purchase_date(self):
        """purchase_date=None results in an empty acquisition_date string."""
        row = {
            "asset_purchase_date": None,
            "asset_purchase_amount": 0.0,
            "asset_disposal_date": None,
            "asset_in_before": 0.0,
            "asset_out_before": 0.0,
            "asset_in_during": 0.0,
            "depreciated_before": 0.0,
            "depreciated_during": 0.0,
            "asset_method": None,
            "asset_percentage": None,
        }
        options = self._make_options(date(2024, 1, 1), date(2024, 12, 31))
        cols = self.handler._compute_columns(options, row)
        self.assertEqual(cols["acquisition_date"], "")

    # --- Integration tests: options initializer, line generator, grouping ---

    def _get_report_and_options(self, date_from="2024-01-01", date_to="2024-12-31"):
        report = self.env.ref("xx_it_depreciation_schedule.it_assets_report")
        options = report.get_options({})
        options["date"]["date_from"] = date_from
        options["date"]["date_to"] = date_to
        return report, options

    def test_custom_options_initializer_balance_name_empty(self):
        _report, options = self._get_report_and_options()
        col = next(c for c in options["columns"] if c["expression_label"] == "balance")
        self.assertEqual(col["name"], "")

    def test_custom_options_initializer_subheaders_set(self):
        _report, options = self._get_report_and_options()
        subheader_names = [s["name"] for s in options.get("custom_columns_subheaders", [])]
        self.assertIn("Assets", subheader_names)
        self.assertIn("Depreciation", subheader_names)
        self.assertIn("Book Value", subheader_names)
        self.assertIn("Characteristics", subheader_names)

    def test_custom_options_initializer_date_columns_renamed(self):
        """Date boundary columns have their names replaced with formatted dates."""
        _report, options = self._get_report_and_options()
        original_names = {"date from", "date to"}
        for expr in ("assets_date_from", "depre_date_from", "assets_date_to", "depre_date_to"):
            col = next(c for c in options["columns"] if c["expression_label"] == expr)
            self.assertNotIn(col["name"], original_names, f"{expr} name was not replaced")

    def test_generate_report_lines_empty(self):
        report, options = self._get_report_and_options(date_from="2099-01-01", date_to="2099-12-31")
        lines, totals = self.handler._generate_report_lines(report, options)
        self.assertEqual(lines, [])
        self.assertIsInstance(totals, dict)

    def test_generate_report_lines_with_asset(self):
        asset = self._create_asset(asset_date=date(2024, 6, 1))
        report, options = self._get_report_and_options()
        lines, totals = self.handler._generate_report_lines(report, options)
        asset_ids = [report._get_model_info_from_id(ln["id"])[1] for ln in lines]
        self.assertIn(asset.id, asset_ids)
        line = next(ln for ln in lines if report._get_model_info_from_id(ln["id"])[1] == asset.id)
        self.assertEqual(line["level"], 2)
        self.assertFalse(line["unfoldable"])
        self.assertIn("assets_account_id", line)
        self.assertIsInstance(line["columns"], list)
        self.assertTrue(line["columns"])

    def test_generate_report_lines_totals_accumulate(self):
        self._create_asset(asset_date=date(2024, 6, 1))
        report, options = self._get_report_and_options()
        _lines, totals = self.handler._generate_report_lines(report, options)
        col_group_key = options["columns"][0]["column_group_key"]
        group_totals = totals[col_group_key]
        # assets_date_to should be non-zero (1000.0 purchase amount)
        self.assertGreater(group_totals["assets_date_to"], 0.0)

    def test_group_lines_by_account_empty_input(self):
        report, options = self._get_report_and_options()
        result = self.handler._group_lines_by_account(report, [], options)
        self.assertEqual(result, [])

    def test_group_lines_by_account_structure(self):
        _asset = self._create_asset(asset_date=date(2024, 6, 1))
        report, options = self._get_report_and_options()
        lines, _ = self.handler._generate_report_lines(report, options)
        self.assertTrue(lines, "Expected at least one asset line")
        grouped = self.handler._group_lines_by_account(report, lines, options)
        levels = [ln["level"] for ln in grouped]
        self.assertIn(1, levels)
        self.assertIn(2, levels)
        account_group = next(ln for ln in grouped if ln["level"] == 1)
        self.assertTrue(account_group["unfoldable"])
        self.assertIsInstance(account_group["columns"], list)

    def test_group_lines_by_account_two_categories(self):
        """Assets from two different accounts appear in separate groups."""
        self._create_asset(asset_date=date(2024, 1, 1))
        self.env["asset.asset"].create(
            {
                "name": "Second category asset",
                "category_id": self.asset_category_2.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
                "purchase_amount": 500.0,
                "purchase_date": date(2024, 1, 1),
            }
        )
        report, options = self._get_report_and_options()
        lines, _ = self.handler._generate_report_lines(report, options)
        grouped = self.handler._group_lines_by_account(report, lines, options)
        account_groups = [ln for ln in grouped if ln["level"] == 1]
        self.assertGreaterEqual(len(account_groups), 2)

    def test_dynamic_lines_generator_with_asset_has_total(self):
        _asset = self._create_asset(asset_date=date(2024, 6, 1))
        report, options = self._get_report_and_options()
        result = self.handler._dynamic_lines_generator(report, options, {})
        self.assertIsInstance(result, list)
        self.assertTrue(result)
        # Result is list of (sequence, line) tuples
        self.assertEqual(result[-1][0], 0)
        total_line = result[-1][1]
        self.assertIn("Total", total_line["name"])
        self.assertEqual(total_line["level"], 1)
        self.assertFalse(total_line["unfoldable"])

    def test_dynamic_lines_generator_empty_no_total(self):
        report, options = self._get_report_and_options(date_from="2099-01-01", date_to="2099-12-31")
        result = self.handler._dynamic_lines_generator(report, options, {})
        self.assertEqual(result, [])
