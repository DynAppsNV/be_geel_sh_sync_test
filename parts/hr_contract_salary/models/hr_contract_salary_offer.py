# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.hr_contract_salary.utils.hr_version import requires_hr_version_context
from werkzeug.urls import url_encode
from odoo.exceptions import ValidationError


class HrContractSalaryOffer(models.Model):
    _name = 'hr.contract.salary.offer'
    _description = 'Salary Package Offer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        contract_id = result.get('employee_contract_id')
        if contract_id:
            contract = self.env['hr.contract'].browse(contract_id)
            result['employee_id'] = contract.employee_id.id
        for field in fields:
            if field == 'access_token' and 'applicant_id' in result:
                result['access_token'] = uuid.uuid4().hex
            if field.startswith('x_') and 'active_id' in self.env.context:
                model = self.env.context.get('active_model')
                if model == "hr.version" and field in self.env[model]:
                    version = self.env[model].browse(self.env.context['active_id'])
                    result[field] = version[field]
                elif model == "hr.applicant" and field in self.env["hr.version"] and "default_contract_template_id" in self.env.context:
                    version = self.env["hr.version"].browse(self.env.context['default_contract_template_id'])
                    result[field] = version[field]
        return result

    display_name = fields.Char(string="Title", compute="_compute_display_name", readonly=False, store=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        compute="_compute_company_id",
        store=True,
        default=lambda self: self.env.company.id,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    contract_template_id = fields.Many2one(
        'hr.version', compute="_compute_contract_template_id", store=True, readonly=False,
        domain="['|', ('employee_id', '=', False), ('id', '=', employee_version_id)]", tracking=True)
    sign_template_id = fields.Many2one(
        'sign.template', compute='_compute_sign_template_id', readonly=False, store=True, string="PDF Sign Template",
        help="Default document that the applicant will have to sign to accept a contract offer.")
    sign_template_signatories_ids = fields.One2many(
        'hr.contract.signatory', 'offer_id', compute="_compute_sign_template_signatories_ids",
        store=True, readonly=False)
    state = fields.Selection([
        ('open', 'In Progress'),
        ('half_signed', 'Partially Signed'),
        ('full_signed', 'Fully Signed'),
        ('expired', 'Expired'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], default='open', tracking=True)
    refusal_reason = fields.Many2one('hr.contract.salary.offer.refusal.reason', string="Refusal Reason", tracking=True)
    offer_create_date = fields.Date("Offer Create Date", compute="_compute_offer_create_date", readonly=True)
    refusal_date = fields.Date("Refusal Date")
    sign_request_ids = fields.Many2many('sign.request', string='Requested Signatures')
    employee_version_id = fields.Many2one('hr.version', tracking=True,
        store=True, compute="_compute_employee_version_id", inverse='_inverse_employee_version_id',
        index='btree_not_null')
    employee_id = fields.Many2one('hr.employee', tracking=True, domain=[('version_ids', '!=', False)])
    applicant_id = fields.Many2one('hr.applicant', index=True, tracking=True)
    applicant_name = fields.Char(related='applicant_id.partner_name')
    final_yearly_costs = fields.Monetary("Employer Budget", aggregator="avg", store=True, tracking=True,
        compute="_compute_offer_values_from_template")
    job_title = fields.Char(tracking=True, store=True, readonly=False,
        compute="_compute_offer_values_from_template")
    employee_job_id = fields.Many2one('hr.job', tracking=True, store=True, readonly=False,
        compute="_compute_offer_values_from_template")
    department_id = fields.Many2one('hr.department', tracking=True, store=True, readonly=False,
        compute="_compute_offer_values_from_template")
    contract_start_date = fields.Date(tracking=True, default=fields.Date.context_today,
        help="For employees, The contract start date determines whether this offer creates a new contract or amends an existing one. If the selected start date falls within the period of an existing contract for the employee, it will be treated as an amendment rather than a new contract.")
    contract_end_date = fields.Date(tracking=True, store=True, compute="_compute_contract_end_date", readonly=False)
    access_token = fields.Char('Access Token', copy=False, tracking=True, store=True, compute="_compute_token")
    validity_days_count = fields.Integer("Validity Days Count",
                              compute="_compute_validity_days_count",
                              store=True, readonly=False)
    offer_end_date = fields.Date('Offer Expiration', readonly=False,
                                 copy=False, tracking=True)
    url = fields.Char('Link', compute='_compute_url')
    is_half_sign_state_required = fields.Boolean(
        compute="_compute_is_half_sign_state_required",
        compute_sudo=True,
        export_string_translation=False
    )
    contract_type_id = fields.Many2one(related='contract_template_id.contract_type_id', string='Contract Type', readonly=True, store=False)
    has_sign_template = fields.Boolean(compute="_compute_has_sign_template")
    is_contract_amendment = fields.Boolean(compute="_compute_is_contract_amendment")
    future_version_date = fields.Date(compute='_compute_future_version_date')

    @api.constrains('contract_start_date', 'contract_end_date')
    def _check_dates_validity(self):
        """Validates that a contract start date exists and is not after the contract end date."""
        for offer in self:
            if not offer.contract_start_date:
                raise ValidationError(self.env._("A contract start date is required."))
            if offer.contract_end_date and offer.contract_start_date > offer.contract_end_date:
                raise ValidationError(self.env._("The contract start date cannot be after the contract end date."))

    @requires_hr_version_context()
    def _get_version(self):
        self.ensure_one()

        employee = self.employee_id or self.env['hr.employee'].with_user(SUPERUSER_ID).sudo().create({
                'name': self.applicant_id.partner_name if self.applicant_id else 'Simulation Employee',
                'private_phone': self.applicant_id.partner_phone if self.applicant_id else False,
                'private_email': self.applicant_id.email_from if self.applicant_id else False,
                'active': False,
                'country_id': self.company_id.country_id.id,
                'private_country_id': self.company_id.country_id.id,
                'certificate': False,  # To force encoding it
                'company_id': self.company_id.id,
            })

        if self.contract_template_id:
            employee.version_id.write(
                self.env['hr.version'].get_values_from_contract_template(self.contract_template_id)
            )
        return employee.current_version_id

    @api.depends('contract_template_id')
    def _compute_has_sign_template(self):
        for offer in self:
            if offer.employee_id:
                offer.has_sign_template = offer.contract_template_id.contract_update_template_id
            else:
                offer.has_sign_template = offer.contract_template_id.sign_template_id

    @api.depends('contract_template_id.sign_template_id', 'contract_template_id.contract_update_template_id')
    def _compute_sign_template_id(self):
        for offer in self:
            if offer.contract_template_id:
                if offer.employee_id and offer.employee_id.active:
                    sign_template = offer.contract_template_id.contract_update_template_id
                else:
                    sign_template = offer.contract_template_id.sign_template_id

                # Update only if a template exists; otherwise, keep the current value
                if sign_template:
                    offer.sign_template_id = sign_template

    def _copy_contract_template_signatories(self):
        self.ensure_one()
        if self.employee_id and self.employee_id.active:
            contract_template_signatories_copy = self.contract_template_id.contract_update_signatories_ids.copy()
        else:
            contract_template_signatories_copy = self.contract_template_id.sign_template_signatories_ids.copy()
        # Must unlink the signatory from the contract template, will be linked to the offer with the SET command
        contract_template_signatories_copy.contract_template_id = False
        contract_template_signatories_copy.update_contract_template_id = False
        return [(5, 0, 0)] + [(6, 0, contract_template_signatories_copy.ids)]

    @api.depends('sign_template_id', 'contract_template_id', 'has_sign_template')
    def _compute_sign_template_signatories_ids(self):
        for offer in self:
            if offer.contract_template_id and offer.has_sign_template:
                offer.sign_template_signatories_ids = offer._copy_contract_template_signatories()
            else:
                offer.sign_template_signatories_ids = self.env['hr.contract.signatory'].create_empty_signatories(offer.sign_template_id)

    @api.depends('contract_template_id.sign_template_signatories_ids')
    def _compute_is_half_sign_state_required(self):
        for offer in self:
            offer.is_half_sign_state_required = len(offer.sign_template_signatories_ids) != 1

    @api.depends("access_token", "final_yearly_costs")
    def _compute_url(self):
        base_url = self.env['hr.contract.salary.offer'].get_base_url()
        for offer in self:
            offer.url = base_url \
                      + f"/salary_package/simulation/offer/{offer._origin.id}" \
                      + f"?final_yearly_costs={round(offer.final_yearly_costs, 2)}" \
                      + (f"&token={offer.access_token}" if offer.access_token else "")

    @api.depends("employee_id", "applicant_id")
    def _compute_token(self):
        for offer in self:
            if not offer.access_token and (not offer.employee_id or not offer.employee_id.user_id):
                offer.access_token = uuid.uuid4().hex

    @api.depends('applicant_id', 'employee_version_id', 'employee_id')
    def _compute_display_name(self):
        for offer in self:
            if offer.applicant_id:
                name = offer.applicant_id.employee_id.name or \
                    offer.applicant_id.partner_id.name or \
                    offer.applicant_id.partner_name
            else:
                name = offer.employee_id.name
            offer.display_name = _("Offer for %(recipient)s", recipient=name) if name else ""

    @api.depends('create_date')
    def _compute_offer_create_date(self):
        for offer in self:
            offer.offer_create_date = offer.create_date and offer.create_date.date() or fields.Date.today()

    @api.depends('offer_create_date', 'offer_end_date')
    def _compute_validity_days_count(self):
        for offer in self:
            offer.validity_days_count = (offer.offer_end_date - offer.offer_create_date).days \
                if offer.offer_end_date else False

    @api.depends('employee_id', 'applicant_id')
    def _compute_company_id(self):
        for offer in self:
            if offer.employee_id:
                offer.company_id = offer.employee_id.company_id
            elif offer.applicant_id:
                offer.company_id = offer.applicant_id.company_id
            else:
                offer.company_id = self.env.company.id

    @api.depends('employee_id', 'contract_start_date')
    def _compute_employee_version_id(self):
        for offer in self:
            if offer.employee_id:
                contract_start_date = offer.contract_start_date or fields.Date.today().replace(day=1)
                offer.employee_version_id = offer.employee_id._get_version(contract_start_date)

    @api.depends('employee_id')
    def _compute_contract_template_id(self):
        for offer in self:
            if not offer.applicant_id:
                offer.contract_template_id = offer.employee_id.version_id

    @api.depends('contract_template_id')
    def _compute_offer_values_from_template(self):
        for offer in self:
            if offer.contract_template_id:
                offer.final_yearly_costs = offer.contract_template_id.final_yearly_costs
                offer.job_title = offer.contract_template_id.job_id.name
                offer.employee_job_id = offer.contract_template_id.job_id
                offer.department_id = offer.contract_template_id.department_id
                offer.company_id = offer.contract_template_id.company_id
            else:
                offer.company_id = offer.env.company.id

    @api.depends('employee_version_id.contract_date_start', 'employee_version_id.contract_date_end', 'contract_start_date')
    def _compute_is_contract_amendment(self):
        for offer in self:
            contract_start_date = offer.contract_start_date or fields.Date.today().replace(day=1)
            offer.is_contract_amendment = (
                offer.employee_version_id
                and offer.employee_version_id.contract_date_start
                and offer.employee_version_id.contract_date_start <= contract_start_date
                and (
                    not offer.employee_version_id.contract_date_end
                    or offer.employee_version_id.contract_date_end >= contract_start_date
                )
            )

    @api.depends('employee_id.version_ids.date_start', 'contract_start_date', 'state')
    def _compute_future_version_date(self):
        for offer in self:
            if offer.employee_id and offer.state in ['open', 'half_signed']:
                contract_start_date = offer.contract_start_date or fields.Date.today().replace(day=1)
                offer.future_version_date = offer.employee_id.version_ids.filtered(
                    lambda v: v.date_start >= contract_start_date
                ).sorted("date_start")[:1].date_start
            else:
                offer.future_version_date = False

    @api.depends('is_contract_amendment', 'employee_version_id.contract_date_end')
    def _compute_contract_end_date(self):
        for offer in self:
            if offer.is_contract_amendment:
                offer.contract_end_date = offer.employee_version_id.contract_date_end

    def _inverse_employee_version_id(self):
        for offer in self:
            offer.employee_id = offer.employee_version_id.employee_id

    @api.onchange('employee_job_id')
    def _onchange_employee_job_id(self):
        self.job_title = self.employee_job_id.name
        if self.employee_job_id.department_id:
            self.department_id = self.employee_job_id.department_id

    def action_open_refuse_wizard(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_contract_salary.open_refuse_wizard")
        return {
            **action,
            'context': {
                'dialog_size': 'medium',
            },
        }

    def action_refuse_offer(self, message=None, refusal_reason=None):
        self.unlink_archived_version_offer()
        if not message:
            message = _("%s manually set the Offer to Refused", self.env.user.name)
        self.write({
            'state': 'refused',
            'refusal_reason': refusal_reason,
            'refusal_date': fields.Date.today()
        })
        for offer in self:
            offer.message_post(body=message)

    def action_jump_to_offer(self):
        self.ensure_one()
        url = f'/salary_package/simulation/offer/{self.id}'
        if self.access_token:
            url += '?' + url_encode({'token': self.access_token})
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def unlink(self):
        self.unlink_archived_version_offer()
        # Delete the employee if it is archived and the number of offers of an
        # applicant to delete is equal to the number of offers linked to that applicant
        offers_with_archived_employee = self.filtered(lambda o: not o.applicant_id.employee_id.active)
        offers_by_applicant = offers_with_archived_employee.grouped('applicant_id')
        employee_to_unlink = self.env['hr.employee']
        for applicant, offers in offers_by_applicant.items():
            if len(offers) == applicant.salary_offers_count:
                employee_to_unlink |= applicant.employee_id
        employee_to_unlink.unlink()
        return super().unlink()

    def _cron_update_state(self):
        self.search([
            ('state', 'in', ['open', 'half_signed']),
            ('offer_end_date', '<', fields.Date.today()),
        ]).write({'state': 'expired'})

    def action_send_by_email(self):
        self.ensure_one()
        try:
            template_id = self.env.ref('hr_contract_salary.mail_template_send_offer').id
        except ValueError:
            template_id = False
        try:
            template_applicant_id = self.env.ref('hr_contract_salary.mail_template_send_offer_applicant').id
        except ValueError:
            template_applicant_id = False
        if self.applicant_id:
            default_template_id = template_applicant_id
        else:
            default_template_id = template_id

        ctx = {
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_light",
            'default_model': 'hr.contract.salary.offer',
            'default_res_ids': self.ids,
            'default_template_id': default_template_id,
            'offer_id': self.id,
            'access_token': self.access_token,
            'validity_end': self.offer_end_date,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [[False, 'form']],
            'target': 'new',
            'context': ctx,
        }

    def action_view_signature_request(self):
        self.ensure_one()
        pending_sign_requests = self.sign_request_ids.filtered(lambda r: r.state != 'signed')
        if len(pending_sign_requests) == 1:
            return pending_sign_requests.go_to_document()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Signature Requests',
            'view_mode': 'kanban,list',
            'res_model': 'sign.request',
            'domain': [('id', 'in', pending_sign_requests.ids)]
        }

    def action_edit_offer_signatories(self):
        self.ensure_one()
        return {
            'name': self.env._("Edit PDF Template Signatories"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'res_model': 'hr.contract.signatory',
            'target': 'new',
            'domain': [('id', 'in', self.sign_template_signatories_ids.ids)],
        }

    def action_view_version(self):
        self.ensure_one()
        version = (
            self.env['hr.version'].with_context(active_test=False).search([('originated_offer_id', '=', self.id)], order="active desc, id desc", limit=1)
            or self.employee_version_id
            or self.env['hr.version'].with_context(active_test=False).search([('applicant_id', '=', self.applicant_id.id)], order="active desc, id desc", limit=1)
        )
        if self.state == 'half_signed':
            action = self.env.ref('hr_contract_salary.action_view_partially_signed_contract_statbutton')._get_action_dict()
        else:
            action = self.env.ref('hr_contract_salary.action_view_contract_statbutton')._get_action_dict()

        action['res_id'] = self.employee_id.id or self.applicant_id.employee_id.id or version.employee_id.id
        action['context'] = {'version_id': version.id}
        return action

    def _mail_get_partners(self, introspect_fields=False):
        return {
            offer.id: (offer.applicant_id.partner_id + offer.employee_id.work_contact_id)
            for offer in self
        }

    def _mail_get_primary_email(self):
        # Override as there is no "_primary_email" defined here, it is a related
        return {
            record.id: record.applicant_id.email_from or record.employee_id.work_email
            for record in self
        }

    @api.constrains('applicant_id', 'employee_id')
    def _check_applicant_id_or_employee_id(self):
        for offer in self:
            if not (offer.applicant_id or offer.employee_id):
                raise ValidationError(
                    self.env._("An offer must be linked to either an applicant or an employee.")
                )

    def unlink_archived_version_offer(self):
        archived_versions = self.env['hr.version'].search([
            ('originated_offer_id', 'in', self.ids),
            ('active', '=', False)
        ])
        if archived_versions:
            archived_versions.sign_request_ids.write({'state': 'canceled', 'active': False})
            archived_versions.unlink()

    def _archive_future_versions(self, version=None):
        """
        Archive all versions that come after the provided version.
        If no version is provided, fallback to archiving from the contract_start_date.
        """
        self.ensure_one()
        if not self.employee_id:
            return

        # To ensure at least one version remains active
        version_to_keep = version or self.employee_version_id
        if version:
            cutoff_date = version.date_version
        else:
            cutoff_date = self.contract_start_date or fields.Date.today().replace(day=1)
        future_versions = self.employee_id.version_ids.filtered(
            lambda v: v != version_to_keep and v.date_version >= cutoff_date
        )
        if future_versions:
            future_versions.write({'active': False})
            future_versions.flush_recordset(['active'])
