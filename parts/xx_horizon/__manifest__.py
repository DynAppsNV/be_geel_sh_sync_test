# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Horizon",
    "version": "19.0.1.0.0",
    "author": "dynapps",
    "summary": "Horizon Module",
    "sequence": 999,
    "category": "Custom",
    "website": "https://www.odoo.com/",
    "depends": ["xx_base", "account", "xx_credit_limit", "queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "views/sync_record_views.xml",
        "views/res_config_settings_view.xml",
        "views/horizon_menu.xml",
    ],
    "demo": [],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
