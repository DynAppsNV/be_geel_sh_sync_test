{
    "name": "Dynamic Approver for Purchase Approvals",
    "version": "19.0.1.0.0",
    "author": "dynapps",
    "website": "https://www.dynapps.eu",
    "category": "Approvals",
    "license": "LGPL-3",
    "depends": [
        "xx_base",
    ],
    "data": [
        "data/sign_item_role_data.xml",
        "security/ir.model.access.csv",
        "views/studio_approval_rule_views.xml",
        "views/po_approval_matrix_views.xml",
        "views/purchase_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
