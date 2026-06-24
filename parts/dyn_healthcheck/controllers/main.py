import json
import traceback
from datetime import datetime, timedelta
from time import time

from odoo import http
from odoo.http import request


class Healthcheck(http.Controller):
    @staticmethod
    def get_defaults():
        """
        Makes it easy to change default values by inheritance

        :return: all defaults in a dict
        """
        return {"cron_minutes": 30}

    @http.route(["/health"], type="http", auth="public")
    def health(self):
        try:
            request.env["res.users"].sudo().search([], limit=1)
            services, critical_ok = self.extra_services()
            return json.dumps(
                {
                    "status": critical_ok and "OK" or "NOT OK",
                    "time": time(),
                    "services": services,
                }
            )
        except Exception:
            return json.dumps({"status": "NOT OK", "time": time()})

    def extra_services(self):
        """return a dict with all the extra services, to make inheritance simple
        when a service is critical, you can also add it to critical_ok
        """
        services = {}
        critical_ok = True

        cron, cron_ok = self.check_cron()
        services.update(cron=cron)
        critical_ok = critical_ok and cron_ok

        return services, critical_ok

    def check_cron(self):
        """return status of odoo cron jobs and healthy boolean
        :return: (dict,bool)
        """
        try:
            cron_minutes = self.get_defaults().get("cron_minutes", 30)
            checktime = datetime.now() - timedelta(minutes=cron_minutes)
            domain = [
                ("active", "=", True),
                ("nextcall", "<", checktime),
            ]
            res = request.env["ir.cron"].sudo().search(domain, limit=1)
            if res:
                return {"name": "Odoo Cron", "status": "NOT OK"}, False
            else:
                return {"name": "Odoo Cron", "status": "OK"}, True
        except Exception:
            return_data = {
                "name": "Odoo Cron",
                "status": "ERROR",
                "traceback": traceback.format_exc(),
            }
            return return_data, False
