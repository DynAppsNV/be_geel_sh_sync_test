from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_co_dian import xml_utils


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_co_dian_enable_update_data = fields.Boolean(compute='_compute_l10n_co_dian_enable_update_data')

    @api.depends_context('company')
    @api.depends('l10n_latam_identification_type_id', 'vat')
    def _compute_l10n_co_dian_enable_update_data(self):
        for partner in self:
            company = self.env.company
            partner.l10n_co_dian_enable_update_data = (
                company.account_fiscal_country_id.code == 'CO'
                and partner.l10n_latam_identification_type_id
                and partner.vat
                and not partner.parent_id
            )

    def button_l10n_co_dian_refresh_data(self):
        self._l10n_co_dian_update_data(self.env.company)

    def _l10n_co_dian_update_data(self, company):
        self.ensure_one()
        partner = self.commercial_partner_id
        data = partner._l10n_co_dian_call_get_acquirer({
            'identification_type': partner._l10n_co_edi_get_carvajal_code_for_identification_type(),
            'identification_number': partner._get_vat_without_verification_code(),
            'company': company,
        })

        if not data or data.get('email') == partner.email:
            return
        if not partner.email:
            partner.write(data)
            return

        if partner.child_ids.filtered(lambda p: 'invoice' in p.type):
            raise UserError(self.env._(
                "This contact has already been updated with DIAN information, please review the related invoicing address contact and see if it matches the data returned from DIAN:\nEmail: %(partner_email)s\nName: %(partner_name)s",
                partner_email=data.get('email'),
                partner_name=data.get('name'),
            ))

        self.env['res.partner'].create({
            **data,
            'parent_id': partner.id,
            'type': 'invoice',
        })

    @api.model
    def _l10n_co_dian_call_get_acquirer(self, data: dict):
        if not self.env.ref('l10n_co_dian.get_acquirer', raise_if_not_found=False):
            # Could happen when the user did not update their db
            return dict()

        response = xml_utils._build_and_send_request(
            self,
            payload={
                'identification_type': data['identification_type'],
                'identification_number': data['identification_number'],
                'soap_body_template': "l10n_co_dian.get_acquirer",
            },
            service='GetAcquirer',
            company=data['company'],
        )

        if response['status_code'] != 200:
            return dict()

        root = etree.fromstring(response['response'])
        return {
            'email': root.findtext('.//{*}ReceiverEmail'),
            'name': root.findtext('.//{*}ReceiverName'),
        }
