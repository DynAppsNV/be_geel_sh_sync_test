from odoo import fields, models


class ModuleCustomFields(models.TransientModel):
    _name = "xx.module.custom.fields"
    _description = "Module Custom Fields"

    settings_id = fields.Many2one(
        comodel_name="xx.dynapps.export.settings", required=True, readonly=True
    )
    module_id = fields.Many2one(comodel_name="ir.module.module", string="Module", required=True)
    module_name = fields.Char(compute="_compute_module_name")
    model_id = fields.Many2one(comodel_name="ir.model", string="Model", required=True)
    model_name = fields.Char(compute="_compute_model_name")
    field_ids = fields.Many2many(comodel_name="ir.model.fields", string="Fields")

    def _compute_module_name(self):
        for rec in self:
            rec.module_name = (
                f"{rec.module_id.name} ({rec.module_id.shortdesc})"
                if rec.module_id.shortdesc
                else rec.module_id.name
            )

    def _compute_model_name(self):
        for rec in self:
            rec.model_name = f"{rec.model_id.model} ({rec.model_id.name})"
