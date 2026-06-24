from odoo import http
from odoo.http import request


class IntrastatExportController(http.Controller):
    @http.route("/xx/intrastat/export_xml", type="http", auth="user")
    def export_xml(self, ids=None, declaration_type="extended", **kwargs):  # pragma: no cover
        if ids:
            ids = [int(x) for x in ids.split(",")]
            records = request.env["xx.intrastat.account.move"].sudo().browse(ids)
        else:
            records = request.env["xx.intrastat.account.move"].sudo().search([])

        if declaration_type not in ("standard", "extended"):
            declaration_type = "extended"
        xml_data = records.get_export_xml(declaration_type=declaration_type)

        suffix = "standard" if declaration_type == "standard" else "extended"
        return request.make_response(
            xml_data,
            headers=[
                ("Content-Type", "application/xml"),
                ("Content-Disposition", f"attachment; filename=intrastat_{suffix}.xml"),
            ],
        )
