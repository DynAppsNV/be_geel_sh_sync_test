# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian Registered Cash Register (v2)',
    'version': '1.1',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'author': 'Odoo S.A.',
    'summary': 'Implements the registered cash system, adhering to guidelines by FPS Finance.',
    'description': "Belgian Registered Cash Register for certified cash registers.",
    'depends': ['l10n_be', 'web_enterprise', 'pos_discount', 'pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/point_of_sale_dashboard.xml',
        'views/l10n_be_pos_blackbox_views.xml',
        'views/pos_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/report_invoice.xml',
        'views/pos_daily_report.xml',
        'views/pos_session_views.xml',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_be_pos_blackbox/static/src/backend/test_blackbox_button/*',
        ],
        'point_of_sale._assets_pos': [
            'l10n_be_pos_blackbox/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'l10n_be_pos_blackbox/static/tests/unit/**/*',
            'l10n_be_pos_blackbox/static/src/common/blackbox/**/*',
            'point_of_sale/static/src/app/hooks/pos_hook.js',
        ],
        'web.assets_tests': [
            'l10n_be_pos_blackbox/static/tests/tours/**/',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
