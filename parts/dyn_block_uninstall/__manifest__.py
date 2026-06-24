{
    "name": "Dynapps Block Uninstall",
    "version": "19.0.1.0.0",
    "author": "dynapps",
    "license": "AGPL-3",
    "website": "https://www.dynapps.eu",
    "category": "Dynapps/Custom module",
    "depends": ["base"],
    "data": [
        "views/ir_module.xml",
    ],
    "installable": True,
    "auto_install": True,
    "dyn_required": True,
    "post_init_hook": "post_init_hook",
}
