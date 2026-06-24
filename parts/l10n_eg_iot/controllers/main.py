from odoo import http
from odoo.addons.iot.controllers.main import IoTController


class L10nEgIotController(IoTController):
    @http.route()
    def update_box(self, iot_box, devices):
        res = super().update_box(iot_box, devices)
        iot_identifier = iot_box['identifier']
        box = self._search_box(iot_identifier) or self._search_box(iot_box.get('mac'))

        if box and not box.l10n_eg_proxy_token:
            l10n_eg_proxy_token = iot_box.get('l10n_eg_proxy_token')
            if l10n_eg_proxy_token:
                box.l10n_eg_proxy_token = l10n_eg_proxy_token

        return res
