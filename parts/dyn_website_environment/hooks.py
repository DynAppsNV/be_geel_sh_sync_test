from odoo.tools import config


def pre_init_hook(env):
    if config["test_enable"]:
        env["website"].create(
            {
                "name": "My Custom Website",
                "domain": "http://localhost:8069",
            }
        )
        env.cr.execute("SELECT * FROM website where name = 'My Custom Website'")
        website = env.cr.dictfetchone()
        assert website
        assert website["domain"] == "http://localhost:8069"


def post_init_hook(env):
    # Migration website data
    env.cr.execute("SELECT * FROM website")
    for row in env.cr.dictfetchall():
        website = env["website"].browse(row["id"])
        if website:
            for field_name, _options in env["website"]._server_env_fields.items():
                if field_name in row:
                    website[field_name] = row[field_name]
