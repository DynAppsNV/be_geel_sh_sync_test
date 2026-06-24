{
    "name": "Romania - D300 VAT Report",
    "description": """
        D300 VAT declaration export for Romania (ANAF).
    """,
    "depends": [
        "l10n_ro_reports",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_tax_report_data.xml",
        "wizard/d300_submission_wizard_views.xml",
        "wizard/d300_lock_wizard.xml",
    ],
    "auto_install": True,
    "post_init_hook": "_post_init_hook",
    "author": "Odoo S.A.",
    "license": "OEEL-1",
}
