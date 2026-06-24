from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.service.common import exp_version
import requests
from requests.exceptions import RequestException


FALLBACK_POS_ID = "CDEM0000000001"


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_be_report_counter = fields.Integer(help="Count the number of reports generated for this POS configuration.", default=1)
    l10n_be_blackbox_be_id = fields.Many2one(
        comodel_name="pos.blackbox.be",
        string="POS Blackbox BE",
        help="The blackbox that is linked to this POS configuration.",
    )
    l10n_be_pos_id = fields.Char(
        string="POS ID",
        store=True,
        compute="_compute_pos_id",
        readonly=True,
        help="The ID of the POS configuration. This ID is used to identify the POS configuration in the blackbox.",
    )
    l10n_be_training_mode = fields.Boolean(
        string="Training Mode",
        help="If checked, the POS will be in training mode.",
        default=False,
    )
    pos_version = fields.Char('Odoo Version', compute='_compute_odoo_version')
    establishment_number = fields.Char(string="Establishment Number", help="The establishment number of the company using this POS configuration.")

    @api.depends('l10n_be_blackbox_be_id')
    def _compute_pos_id(self):
        for config in self:
            if config.l10n_be_blackbox_be_id and (not config.l10n_be_pos_id or config.l10n_be_pos_id == FALLBACK_POS_ID):
                try:
                    config.l10n_be_pos_id = self._get_pos_id_from_fdm()
                except UserError:
                    config.l10n_be_pos_id = FALLBACK_POS_ID

    def _get_pos_id_from_fdm(self):
        """Retrieve POS ID from FDM service"""
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not db_uuid:
            raise UserError(_("Database UUID not found."))
        endpoint = "https://fdm.odoo.com/_fdm/pos/sequence/"

        url = f"{endpoint}{db_uuid}"
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.text
        except RequestException as e:
            raise UserError(
                _("Failed to retrieve POS ID from FDM service:\n%s", e)
            )

    def action_request_pos_id(self):
        self.ensure_one()
        if self.l10n_be_pos_id and self.l10n_be_pos_id != FALLBACK_POS_ID:
            raise UserError(_("A valid POS ID is already set for this configuration."))
        try:
            self.l10n_be_pos_id = self._get_pos_id_from_fdm()
        except UserError:
            self.l10n_be_pos_id = FALLBACK_POS_ID
            self.env.cr.commit()
            raise

    def write(self, vals):
        if (vals.get('l10n_be_blackbox_be_id') or self.filtered("l10n_be_pos_id")):
            # TODO-FW-19.1: adapt based on this PR: https://github.com/odoo/odoo/pull/229561
            cash_rounding = self._create_default_cashrounding()
            if cash_rounding:
                vals['cash_rounding'] = True
                vals['rounding_method'] = cash_rounding.id
                vals['only_round_cash_method'] = True
            vals['iface_print_auto'] = True
            vals['iface_print_skip_screen'] = True
        return super().write(vals)

    def _check_l10n_be_before_opening(self):
        for config in self.filtered('l10n_be_pos_id'):
            config._check_blackbox_required()
        for config in self.filtered('l10n_be_blackbox_be_id'):
            config._check_cashier_l10n_be_insz_or_bis_number()
            config._check_cash_rounding()
            config._check_iface_printers()
            config._check_config_company_data()
            config._check_blackbox()

    def open_ui(self):
        self._check_l10n_be_before_opening()
        return super().open_ui()

    def _check_blackbox_required(self):
        for config in self:
            if config.l10n_be_pos_id and not config.l10n_be_blackbox_be_id:
                raise ValidationError(_(
                    "This POS has a registered POS ID and requires a blackbox to be configured."
                ))

    def _check_iface_printers(self):
        for config in self:
            if not config.iface_print_auto:
                raise ValidationError(_("Automatic Receipt Printing must be activated"))
            if not config.iface_print_skip_screen:
                raise ValidationError(_("Skip Preview Screen must be activated"))

    def _check_config_company_data(self):
        for config in self:
            if not config.establishment_number:
                raise ValidationError(_("An establishment number must be set for this POS configuration."))
            if not config.company_id.vat:
                raise ValidationError(_("A VAT number must be set for the company using this POS configuration."))
            if not config.l10n_be_pos_id:
                raise ValidationError(_("A POS ID must be set for this POS configuration."))

    def _check_cashier_l10n_be_insz_or_bis_number(self):
        for config in self:
            if not self.env.user.l10n_be_insz_or_bis_number and not config.module_pos_hr:
                raise ValidationError(
                    _(
                        "%(user)s must have an INSZ or BIS number.",
                        user=self.env.user.name,
                    )
                )

    def _check_cash_rounding(self):
        if self.payment_method_ids.filtered(lambda p: p.is_cash_count):
            if not self.cash_rounding:
                raise ValidationError(_("Cash rounding must be enabled"))
            if (
                self.rounding_method.rounding != 0.05
                or self.rounding_method.rounding_method != "HALF-UP"
            ):
                raise ValidationError(
                    _('The rounding method must be set to 0.05 and "Nearest"')
                )

    @api.constrains('l10n_be_training_mode')
    def _check_l10n_be_training_mode(self):
        for record in self:
            signed_order = self.env['pos.order'].search_count([
                ('session_id.config_id', '=', record.id),
                ('l10n_be_short_signature', '!=', False),
            ], limit=1)

            if signed_order and record.l10n_be_training_mode:
                raise ValidationError(_(
                    "You cannot enable training mode on a POS configuration that has already processed orders."
                ))

    def _check_blackbox(self):
        for config in self:
            if not config.l10n_be_blackbox_be_id.local_ip:
                raise ValidationError(_(
                    "The blackbox must have a local IP address configured."
                ))

    @api.model
    def _create_default_cashrounding(self):
        cash_rounding = self.env.ref('l10n_be_pos_blackbox.default_l10n_be_cash_rounding', raise_if_not_found=False)
        if cash_rounding:
            return cash_rounding
        if self.env.company.chart_template == "be_comp":
            profit_account = self.env.ref(f'account.{self.env.company.id}_a743', raise_if_not_found=False)
            loss_account = self.env.ref(f'account.{self.env.company.id}_a643', raise_if_not_found=False)
            if profit_account and loss_account:
                cash_rounding = self.env['account.cash.rounding'].create({
                    'name': _('Belgian Cash Rounding'),
                    'rounding_method': 'HALF-UP',
                    'rounding': 0.05,
                    'profit_account_id': profit_account.id,
                    'loss_account_id': loss_account.id,
                })
                self.env['ir.model.data']._update_xmlids([
                    {
                        'xml_id': 'l10n_be_pos_blackbox.default_l10n_be_cash_rounding',
                        'record': cash_rounding,
                        'noupdate': True,
                    }
                ])
            return cash_rounding
        return False

    def _compute_odoo_version(self):
        self.pos_version = exp_version()['server_serie']

    @api.constrains('establishment_number')
    def _check_pos_establishment_number(self):
        for config in self:
            if config.establishment_number and not config.is_valid_est_number(config.establishment_number):
                raise ValidationError(
                    _(
                        "Invalid establishment number.\n\n"
                        "An establishment number must meet the following rules:\n"
                        "- It must contain exactly 10 digits\n"
                        "- The first digit must be between 2 and 8\n"
                    )
                )

    @api.model
    def is_valid_est_number(self, value):
        """ Validate an establishment unit number (estNo).
            Rules:
                - Length = 10
                - Digits only
                - Starts with a digit from '2' to '8'
                - Must pass the modulo 97 check
                - Example: 8789456149
        """
        if not value:
            return False

        if not value.isdigit() or len(value) != 10:
            return False

        base = int(value[:8])
        key = int(value[8:])
        expected_key = 97 - (base % 97)
        return key == expected_key
