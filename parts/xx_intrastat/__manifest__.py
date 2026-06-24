# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Intrastat",
    "version": "19.0.1.1.0",
    "author": "dynapps",
    "summary": "Intrastat",
    "sequence": 999,
    "category": "Custom",
    "website": "https://www.odoo.com/",
    "depends": ["xx_base"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/account_intrastat_code_views.xml",
        "views/account_incoterm_views.xml",
        "views/res_partner_views.xml",
        "views/intrastat_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
