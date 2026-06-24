from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.service.common import exp_version


class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.model
    def _load_pos_self_data_fields(self, pos_config_id):
        fields = super()._load_pos_self_data_fields(pos_config_id)
        if pos_config_id.l10n_be_blackbox_be_id:
            fields += ['l10n_be_pos_id']
            if pos_config_id.self_ordering_mode == 'kiosk':
                fields += ['l10n_be_blackbox_be_id', 'establishment_number']
        return fields

    def _load_self_data_models(self):
        models = super()._load_self_data_models()
        if self.l10n_be_blackbox_be_id and self.self_ordering_mode == 'kiosk':
            models += ['pos.blackbox.be']
        return models

    @api.model
    def _load_pos_self_data_read(self, records, config):
        read_records = super()._load_pos_self_data_read(records, config)
        if not read_records:
            return read_records
        if config.l10n_be_blackbox_be_id and config.self_ordering_mode == 'kiosk':
            record = read_records[0]
            record['_self_ordering_default_user_insz'] = config.self_ordering_default_user_id.l10n_be_insz_or_bis_number
            record['_server_version'] = exp_version()
        return read_records

    def action_open_wizard(self):
        self._check_l10n_be_before_opening()
        return super().action_open_wizard()

    def _check_cashier_l10n_be_insz_or_bis_number(self):
        super()._check_cashier_l10n_be_insz_or_bis_number()
        for config in self:
            if config.self_ordering_mode == 'kiosk':
                if not config.self_ordering_default_user_id.l10n_be_insz_or_bis_number:
                    raise ValidationError(
                        _("%s user must have a INSZ or BIS number.", config.self_ordering_default_user_id.name)
                    )
