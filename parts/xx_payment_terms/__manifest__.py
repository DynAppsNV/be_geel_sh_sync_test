# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "PaymentTerms",
    "version": "19.0.1.0.0",
    "author": "dynapps",
    "summary": "Payment Terms Module",
    "sequence": 999,
    "category": "Custom",
    "website": "https://www.odoo.com/",
    "depends": ["xx_base", "account"],
    "data": ["security/ir.model.access.csv", "wizard/account_payment_register_views.xml"],
    "demo": [],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
