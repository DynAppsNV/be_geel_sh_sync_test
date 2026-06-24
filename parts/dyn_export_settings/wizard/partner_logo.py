import base64
import os

from odoo import fields, models
from odoo.tools import file_open


class PartnerImage(models.TransientModel):
    _name = "xx.partner.logo"
    _description = "Partner Logo"

    settings_id = fields.Many2one(
        comodel_name="xx.dynapps.export.settings", required=True, readonly=True
    )
    partner_id = fields.Many2one(comodel_name="res.partner", required=True, readonly=True)
    logo = fields.Image(related="partner_id.image_1920", readonly=True)
    original_logo = fields.Image(compute="_compute_logo", readonly=True)
    filename = fields.Char(required=True, readonly=True)
    logo_diff = fields.Boolean(compute="_compute_logo", string="Different")

    def _compute_logo(self):
        for rec in self:
            try:
                with file_open(
                    os.path.join(
                        self.env["dyn.export.settings.mixin"]._dyn_export_get_base_module().name,
                        f"static/img/{rec.filename}",
                    ),
                    mode="rb",
                ) as file:
                    old_logo = file.read()
            except FileNotFoundError:
                old_logo = None
            attachment = self.env["dyn.export.settings.mixin"]._get_attachment(
                rec.partner_id, "image_1920"
            )
            rec.logo_diff = old_logo != (
                attachment and attachment._file_read(attachment.store_fname) or None
            )
            rec.original_logo = base64.b64encode(old_logo) if old_logo else False
