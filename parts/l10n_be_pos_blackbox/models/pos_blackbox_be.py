from odoo import models, fields, api


class PosBlackboxBe(models.Model):
    _name = "pos.blackbox.be"
    _inherit = ["pos.load.mixin"]
    _description = "POS Blackbox BE"

    name = fields.Char(compute="_compute_name")
    fdm_id = fields.Char(
        string="FDM ID",
        required=True,
        help="The ID of the blackbox is written on the back of the device.",
    )
    pos_config_ids = fields.One2many(
        comodel_name="pos.config",
        inverse_name="l10n_be_blackbox_be_id",
        string="POS Configurations",
        help="The POS configurations that are linked to this blackbox.",
    )
    local_ip = fields.Char(
        string="Local IP",
        help="The local IP will automatically be set when the blackbox is registered.",
    )
    use_lna = fields.Boolean(string="Use Local Network Access")

    @api.model
    def _load_pos_data_domain(self, data, config):
        if not data.get('pos.config'):
            return False
        return [('id', '=', data['pos.config'][0]['l10n_be_blackbox_be_id'])]

    @api.depends("fdm_id")
    def _compute_name(self):
        for record in self:
            record.name = f"Blackbox - {record.fdm_id}"
