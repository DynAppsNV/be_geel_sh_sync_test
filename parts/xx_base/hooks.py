def post_init_hook(env):
    key = "account_peppol.edi.mode"
    param = env["ir.config_parameter"].search([("key", "=", key)])
    if not param:
        param = env["ir.config_parameter"].create({"key": key, "value": "demo"})
        env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "account_peppol.default_account_peppol_edi_mode",
                    "noupdate": True,
                    "record": param,
                },
            ],
        )
