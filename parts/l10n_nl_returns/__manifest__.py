{
    'name': 'Netherlands - Accounting Returns',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Submit your Tax Reports to the Dutch tax authorities through the account returns.
    """,
    'author': 'Odoo S.A.',
    'depends': ['l10n_nl_reports'],
    'data': [
        'views/account_return_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_nl_returns/static/src/scss/account_return.scss',
        ],
    },
    'installable': True,
    'auto_install': ['l10n_nl_reports'],
    'license': 'OEEL-1',
}
