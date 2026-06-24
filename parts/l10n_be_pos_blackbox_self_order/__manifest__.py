# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian Registered Cash Register Self-Order Extension',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'author': 'Odoo S.A.',
    'summary': 'Implements the registered cash system self-order extension, adhering to guidelines by FPS Finance.',
    'description': "Belgian Registered Cash Register Self-Order Extension for certified cash registers.",
    'depends': ['l10n_be_pos_blackbox', 'pos_self_order'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_be_pos_blackbox_self_order/static/src/overrides/**/*',
        ],
        'pos_self_order.assets': [
            'l10n_be_pos_blackbox/static/src/common/**/*',
            'l10n_be_pos_blackbox_self_order/static/src/app/**/*',
            'point_of_sale/static/src/app/hooks/pos_hook.js',
        ],
        'pos_self_order.assets_tests': [
            'l10n_be_pos_blackbox_self_order/static/tests/tours/tour_self_order_blackbox.js',
            'l10n_be_pos_blackbox/static/tests/tours/blackbox_oracle.js',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
