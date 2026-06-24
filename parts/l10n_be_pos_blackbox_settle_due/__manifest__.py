# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian Registered Cash Register Settle Due Extension',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'author': 'Odoo S.A.',
    'summary': 'Implements the registered cash system settle due extension, adhering to guidelines by FPS Finance.',
    'description': "Belgian Registered Cash Register Settle Due Extension for certified cash registers.",
    'depends': ['l10n_be_pos_blackbox', 'pos_settle_due'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_be_pos_blackbox_settle_due/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'l10n_be_pos_blackbox_settle_due/static/src/common/blackbox/**/*',
            'l10n_be_pos_blackbox_settle_due/static/tests/unit/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
