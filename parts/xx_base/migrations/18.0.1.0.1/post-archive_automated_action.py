from odoo import SUPERUSER_ID, api


def migrate(cr, _version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env["base.automation"].search([("name", "=ilike", "Test betaalbewijs leverancier")])
    if action:
        action.action_archive()
