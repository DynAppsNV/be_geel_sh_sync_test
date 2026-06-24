from odoo import fields, models


class ModuleData(models.TransientModel):
    _name = "xx.module.data"
    _description = "Module Data"
    _order = "module_name, model"

    settings_id = fields.Many2one(
        comodel_name="xx.dynapps.export.settings", required=True, readonly=True
    )
    module_id = fields.Many2one(comodel_name="ir.module.module", required=True)
    module_name = fields.Char(related="module_id.name", string="Module Technical Name", store=True)
    model_id = fields.Many2one(string="Model Name", comodel_name="ir.model", required=True)
    model = fields.Char(related="model_id.model", store=True)
    data_filename = fields.Char(required=True)
    settings_tech = fields.Text(compute="_compute_settings")
    settings_tech_diff = fields.Text(compute="_compute_settings_diff")
    has_diff = fields.Boolean(compute="_compute_settings_diff")
    export_order = fields.Integer(compute="_compute_export_order")

    def _compute_settings(self):
        for rec in self:
            rec.settings_tech = (
                rec.env[rec.model_id.model].with_context(module_data=rec)._dyn_export_get_tech()
            )

    def _compute_settings_diff(self):
        for rec in self:
            rec.settings_tech_diff = self.env["dyn.export.settings.mixin"]._dyn_export_get_diff(
                self.env["dyn.export.settings.mixin"]._dyn_export_get_module_data_file_path(
                    rec.module_id, rec.data_filename
                ),
                rec.settings_tech,
            )
            rec.has_diff = bool(rec.settings_tech_diff)

    def _compute_export_order(self):
        for rec in self:
            rec.export_order = self.env[rec.model_id.model]._dyn_export_get_export_order()
