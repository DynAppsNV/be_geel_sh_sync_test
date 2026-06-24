from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_default_receivable_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
        string="Default Account Receivable",
        readonly=False,
        domain="[('account_type', '=', 'asset_receivable')]",
        compute="_compute_account_default_receivable_id",
        inverse="_inverse_account_default_receivable_id",
        help="This is the default receivable account that will be "
        "used on partners that do not have a specific account on them.",
    )
    account_default_payable_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
        string="Default Account Payable",
        readonly=False,
        domain="[('account_type', '=', 'liability_payable')]",
        compute="_compute_account_default_payable_id",
        inverse="_inverse_account_default_payable_id",
        help="This is the default payable account that will be "
        "used on partners that do not have a specific account on them.",
    )

    @api.depends("company_id")
    def _compute_account_default_receivable_id(self):
        ResPartner = self.env["res.partner"]
        account_receivable = ResPartner._fields[
            "property_account_receivable_id"
        ].get_company_dependent_fallback(ResPartner)
        self.account_default_receivable_id = account_receivable

    def _inverse_account_default_receivable_id(self):
        for setting in self:
            self.env["ir.default"].set(
                "res.partner",
                "property_account_receivable_id",
                setting.account_default_receivable_id.id,
                company_id=setting.company_id.id,
            )

    @api.depends("company_id")
    def _compute_account_default_payable_id(self):
        ResPartner = self.env["res.partner"]
        account_payable = ResPartner._fields[
            "property_account_payable_id"
        ].get_company_dependent_fallback(ResPartner)
        self.account_default_payable_id = account_payable

    def _inverse_account_default_payable_id(self):
        for setting in self:
            self.env["ir.default"].set(
                "res.partner",
                "property_account_payable_id",
                setting.account_default_payable_id.id,
                company_id=setting.company_id.id,
            )
