.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
  :target: https://www.gnu.org/licenses/agpl
  :alt: License: AGPL-3

========================
IT Depreciation Schedule
========================

IT Depreciation Schedule
========================

Provides a Depreciation Schedule report (cloned from the standard
``account_asset`` report) that sources its data from the OCA
``l10n_it_asset_management`` asset hierarchy instead of the native Odoo
``account.asset`` model.

Files
-----

New
~~~

+----------------------------------+----------------------------------+
| File                             | Purpose                          |
+==================================+==================================+
| ``mod                            | ``AccountAssetItReportHandler``  |
| els/account_asset_it_report.py`` | — custom report handler          |
+----------------------------------+----------------------------------+
| ``data/account_report_data.xml`` | ``account.report`` record +      |
|                                  | client action                    |
+----------------------------------+----------------------------------+
| ``tests/t                        | Integration tests                |
| est_account_asset_it_report.py`` |                                  |
+----------------------------------+----------------------------------+

Column mapping (OCA → report columns)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------------+----------------------------------------------+
| Column               | OCA source                                   |
+======================+==============================================+
| Acquisition Date     | ``asset.asset.purchase_date``                |
+----------------------+----------------------------------------------+
| Method               | ``asset.depreciation.mode_id.name``          |
+----------------------+----------------------------------------------+
| Duration / Rate      | ``asset.depreciation.percentage``            |
+----------------------+----------------------------------------------+
| Assets opening       | ``purchase_amount`` where                    |
|                      | ``purchase_date < date_from`` (+ ``in``      |
|                      | lines before period)                         |
+----------------------+----------------------------------------------+
| Assets +             | ``asset.depreciation.line`` with             |
|                      | ``move_type='in'`` within period             |
+----------------------+----------------------------------------------+
| Assets −             | closing set to 0 on disposal                 |
+----------------------+----------------------------------------------+
| Assets closing       | opening + in − out                           |
+----------------------+----------------------------------------------+
| Depreciation opening | sum of ``move_type='depreciated'`` lines     |
|                      | before ``date_from``                         |
+----------------------+----------------------------------------------+
| Depreciation +       | sum of ``move_type='depreciated'`` lines     |
|                      | within period                                |
+----------------------+----------------------------------------------+
| Depreciation −       | depreciation balance cleared on disposal     |
+----------------------+----------------------------------------------+
| Depreciation closing | opening + period − on disposal               |
+----------------------+----------------------------------------------+
| Book Value           | assets closing − depreciation closing        |
+----------------------+----------------------------------------------+


Credits
=======

Maintainer
----------

.. image:: /xx_it_depreciation_schedule/static/description/icon.png
  :alt: Dynapps
  :target: https://www.dynapps.eu
  :width: 88
  :height: 88

This module is maintained by Dynapps.