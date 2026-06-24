import json

from odoo import SUPERUSER_ID, http
from odoo.exceptions import AccessError
from odoo.http import Response


class DynappsAnalyticController(http.Controller):
    @http.route("/.dynapps/analytics", type="http", auth="user", csrf=False)
    def main(self, **kwargs):
        if not http.request.env.user.has_group("base.group_system"):
            raise AccessError(http.request.env._("Access denied"))

        env = http.request.env(user=SUPERUSER_ID)

        data = env["xx.dynapps.analytics"].with_context(lang="en_US")._prepare_analytic_data()

        return Response(json.dumps(data), headers={"Content-Type": "application/json"})
