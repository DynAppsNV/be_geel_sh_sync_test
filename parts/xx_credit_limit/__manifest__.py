# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "CreditLimit",
    "version": "19.0.1.0.0",
    "author": "dynapps",
    "summary": "Credit Limit Module",
    "sequence": 999,
    "category": "Custom",
    "website": "https://www.odoo.com/",
    "depends": ["xx_base"],
    "data": [
        "security/ir.model.access.csv",
        "views/credit_line_views.xml",
        "views/credit_line_menus.xml",
        "views/res_partner_views.xml",
        "views/credit_limit_search.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
