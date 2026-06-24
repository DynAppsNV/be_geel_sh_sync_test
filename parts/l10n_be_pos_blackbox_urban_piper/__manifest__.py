# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian Registered Cash Register Urban Piper Extension',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'author': 'Odoo S.A.',
    'summary': 'Implements the registered cash system Urban Piper extension, adhering to guidelines by FPS Finance.',
    'description': "Belgian Registered Cash Register Urban Piper Extension for certified cash registers.",
    'depends': ['l10n_be_pos_blackbox', 'pos_urban_piper'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_be_pos_blackbox_urban_piper/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'l10n_be_pos_blackbox_urban_piper/static/src/**/*',
            'l10n_be_pos_blackbox_urban_piper/static/tests/unit/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
