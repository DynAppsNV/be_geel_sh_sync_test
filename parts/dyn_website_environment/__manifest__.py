{
    "name": "Dynapps website configuration with server_environment",
    "version": "19.0.1.0.0",
    "author": "dynapps",
    "license": "AGPL-3",
    "website": "https://www.dynapps.eu",
    "category": "Dynapps/Custom module",
    "depends": ["server_environment", "website"],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "data": ["views/website.xml"],
    "auto_install": True,
    "installable": True,
}
