{
    "name": "Odoo Analytics | Dynapps",
    "version": "19.0.1.0.0",
    "author": "dynapps",
    "license": "AGPL-3",
    "website": "https://www.dynapps.eu",
    "category": "Technical",
    "depends": ["web"],
    "data": [
        "data/cron.xml",
        "data/ir_config_parameter.xml",
        "security/ir.model.access.csv",
        "views/analytic_views.xml",
    ],
    "external_dependencies": {
        "python": ["sqlparse"],
    },
    "installable": True,
    "auto_install": True,
    "post_init_hook": "post_init_hook",
}
