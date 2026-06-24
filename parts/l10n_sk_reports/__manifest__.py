{
    'name': 'Slovakia - Accounting Reports',
    'icon': '/account/static/description/l10n.png',
    'description': """
Accounting reports for Slovakia
=====================================
This module includes accounting reports for Slovakia, including:
-Balance Sheet + Profit and Loss (XML export)
-Tax report (XML export). For more information, see https://www.financnasprava.sk/sk/podnikatelia/dane/dan-z-pridanej-hodnoty/danove-priznanie
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_sk', 'account_reports'],
    'data': [
        'data/account_return_data.xml',
        'data/annual_statements_menuitem.xml',
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
        'data/annual_statements.xml',
        'data/annual_statements_export.xml',
        'data/tax_report.xml',
        'data/tax_report_export.xml',
        'views/res_company_views.xml',
        'wizard/l10n_sk_generate_annual_statements_report.xml',
        'security/ir.model.access.csv',
    ],
    'demo': ['demo/demo_company.xml'],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
