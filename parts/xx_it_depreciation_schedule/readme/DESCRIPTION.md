# IT Depreciation Schedule

Provides a Depreciation Schedule report (cloned from the standard `account_asset`
report) that sources its data from the OCA `l10n_it_asset_management` asset hierarchy
instead of the native Odoo `account.asset` model.

## Files

### New

| File | Purpose |
|---|---|
| `models/account_asset_it_report.py` | `AccountAssetItReportHandler` — custom report handler |
| `data/account_report_data.xml` | `account.report` record + client action |
| `tests/test_account_asset_it_report.py` | Integration tests |

### Column mapping (OCA → report columns)

| Column | OCA source |
|---|---|
| Acquisition Date | `asset.asset.purchase_date` |
| Method | `asset.depreciation.mode_id.name` |
| Duration / Rate | `asset.depreciation.percentage` |
| Assets opening | `purchase_amount` where `purchase_date < date_from` (+ `in` lines before period) |
| Assets + | `asset.depreciation.line` with `move_type='in'` within period |
| Assets − | closing set to 0 on disposal |
| Assets closing | opening + in − out |
| Depreciation opening | sum of `move_type='depreciated'` lines before `date_from` |
| Depreciation + | sum of `move_type='depreciated'` lines within period |
| Depreciation − | depreciation balance cleared on disposal |
| Depreciation closing | opening + period − on disposal |
| Book Value | assets closing − depreciation closing |
