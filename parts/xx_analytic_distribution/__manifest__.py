# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Analytic Distribution",
    "version": "19.0.1.3.0",
    "author": "dynapps",
    "summary": "Analytic Distribution Module",
    "sequence": 999,
    "category": "Custom",
    "website": "https://www.odoo.com/",
    "depends": ["xx_base"],
    "data": [
        "views/analytic_distribution_view.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "license": "LGPL-3",
}
