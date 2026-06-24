from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Auth settings

    xx_horizon_auth_tenant_id = fields.Char(
        string="Tenant ID",
        config_parameter="xx_horizon.auth_tenant_id",
    )
    xx_horizon_auth_url = fields.Char(
        string="Auth URL",
        config_parameter="xx_horizon.auth_url",
    )
    xx_horizon_auth_client_id = fields.Char(
        string="Client ID",
        config_parameter="xx_horizon.auth_client_id",
    )
    xx_horizon_auth_scope = fields.Char(
        string="Scope",
        config_parameter="xx_horizon.auth_scope",
    )
    xx_horizon_auth_grant_type = fields.Char(
        string="Grant Type",
        config_parameter="xx_horizon.auth_grant_type",
    )
    xx_horizon_auth_client_secret = fields.Char(
        string="Client Secret",
        config_parameter="xx_horizon.auth_client_secret",
    )

    # PAS settings

    xx_horizon_pas_base_url = fields.Char(
        string="PAS Base URL",
        config_parameter="xx_horizon.pas_base_url",
    )

    xx_horizon_pas_contact_endpoint = fields.Char(
        string="PAS Contact Endpoint",
        config_parameter="xx_horizon.pas_contact_endpoint",
    )

    xx_horizon_pas_creditlimit_endpoint = fields.Char(
        string="PAS Credit Limit Endpoint",
        config_parameter="xx_horizon.pas_creditlimit_endpoint",
    )

    xx_horizon_pas_journal_endpoint = fields.Char(
        string="PAS Journal Endpoint",
        config_parameter="xx_horizon.pas_journal_endpoint",
    )

    xx_horizon_pas_currency_endpoint = fields.Char(
        string="PAS Currency Endpoint",
        config_parameter="xx_horizon.pas_currency_endpoint",
    )

    xx_horizon_pas_param_endpoint = fields.Char(
        string="PAS Param Endpoint",
        config_parameter="xx_horizon.pas_param_endpoint",
    )

    xx_horizon_pas_purchase_endpoint = fields.Char(
        string="PAS Purchase Endpoint",
        config_parameter="xx_horizon.pas_purchase_endpoint",
    )
