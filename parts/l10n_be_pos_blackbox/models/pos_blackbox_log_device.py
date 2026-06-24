from odoo import api, models, fields


class PosBlackboxLogDevice(models.Model):
    _name = 'pos.blackbox.log.device'
    _description = 'POS Blackbox Log Device'

    device = fields.Char(string='Device Identifier', required=True)
    _device_unique = models.UniqueIndex('(device)')

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            if vals.get('device'):
                existing = self.search([('device', '=', vals['device'])], limit=1)
                if existing:
                    records |= existing
                else:
                    records |= super().create([vals])
        return records

    @api.model
    def log_device(self, config_id, device):
        """
        Log the device identifier used to open the POS.

        :param config_id: pos.config record
        :param device: string uniquely identifying the device
        """

        if not device:
            return

        config = self.env['pos.config'].browse(config_id)

        if config.l10n_be_blackbox_be_id:
            self.create({'device': device})
            return True
        elif self.search_count([('device', '=', device)]):
            return False
