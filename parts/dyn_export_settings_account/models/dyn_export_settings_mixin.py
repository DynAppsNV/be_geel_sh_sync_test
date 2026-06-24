from odoo import models


class DynExportSettingsMixin(models.AbstractModel):
    _inherit = "dyn.export.settings.mixin"

    def _dyn_export_ignore_field(self, field_name):
        _field = self._fields[field_name]
        if _field.relational:
            if _field.comodel_name.startswith("account"):
                return True
        return super()._dyn_export_ignore_field(field_name)
