def post_init_hook(env):
    companies = env["res.company"].with_context(active_test=False).search([])
    companies._dyn_export_add_xml_id(overwrite=True)
    env["res.partner"].with_context(active_test=False).search(
        [("id", "in", companies.mapped("partner_id").ids)]
    )._dyn_export_add_xml_id(overwrite=True)
