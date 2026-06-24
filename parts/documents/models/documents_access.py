from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools.misc import consteq


class DocumentsAccess(models.Model):
    _name = 'documents.access'
    _description = 'Document / Partner'
    _log_access = False

    document_id = fields.Many2one('documents.document', required=True, bypass_search_access=True, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    role = fields.Selection(
        [('view', 'Viewer'), ('edit', 'Editor')],
        string='Role', required=False, index=True)
    last_access_date = fields.Datetime('Last Accessed On', required=False)
    expiration_date = fields.Datetime('Expiration', index=True)

    _unique_document_access_partner = models.Constraint(
        'unique(document_id, partner_id)',
        "This partner is already set on this document.",
    )
    _role_or_last_access_date = models.Constraint(
        'check (role IS NOT NULL or last_access_date IS NOT NULL)',
        "NULL roles must have a set last_access_date",
    )

    @api.constrains("partner_id")
    def _check_partner_id(self):
        """Avoid to have bad data when the access is created from a public user or in a CRON."""
        forbidden_users = (self.env.ref('base.user_root'), self.env.ref('base.public_user'))
        for access in self:
            if access.partner_id.user_ids in forbidden_users:
                raise ValidationError(_('This user can not be member.'))

    def _prepare_create_values(self, vals_list):
        vals_list = super()._prepare_create_values(vals_list)
        documents = self.env['documents.document'].browse(
            [vals['document_id'] for vals in vals_list])
        documents.check_access('write')
        return vals_list

    def write(self, vals):
        if 'partner_id' in vals or 'document_id' in vals:
            raise AccessError(_('Access documents and partners cannot be changed.'))

        self.document_id.check_access('write')
        return super().write(vals)

    @api.autovacuum
    def _gc_expired(self):
        self.search([('expiration_date', '<=', fields.Datetime.now())], limit=1000).unlink()

    ######################
    # Partner invitation #
    ######################

    def _is_signup_available(self):
        return (
            self.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'
            and self.role
            and (not self.expiration_date or self.expiration_date > fields.Datetime.now())
            and not self.partner_id.with_context(active_test=False).user_ids
        )

    def _get_member_signup_token(self):
        """Token used to invite a member to create a user.

        The token is built using the ID of the access, so we can remove
        the member to invalidate the invitation, or use the expiration
        date.
        """
        self.ensure_one()
        if not self._is_signup_available():
            raise UserError(_('Cannot invite this member.'))

        return tools.hmac(
            self.env(su=True),
            'documents-member-signup-token',
            (self.id, self.partner_id.id),
        )

    @api.model
    def _get_member_from_token(self, member_id, token):
        member_sudo = self.browse(member_id).sudo().exists()
        if not member_sudo or not member_sudo._is_signup_available():
            return False
        if not consteq(member_sudo._get_member_signup_token(), token):
            return False
        return member_sudo

    @api.model
    def _get_signup_url(self, member_id, member_signup_token, access_token, redirect_url):
        """Build the signup URL for the current public user.

        :param member_id: ID of the `documents.access`
        :param member_signup_token: Token of the `documents.access`
        :param access_token: Token of the document (used to redirect
            the user after he signed-up)
        :param redirect_url: The URL where to redirect after the sign-up
        """
        if not member_id or not member_signup_token or not access_token:
            return ''

        # need to get the document from the member, because `_from_access_token`
        # won't return the document if it's in `access_via_link == 'none'`
        member_sudo = self._get_member_from_token(member_id, member_signup_token)
        if not member_sudo:
            return ''

        member_sudo.partner_id.signup_get_auth_param()
        return member_sudo.partner_id._get_signup_url_for_action(url=redirect_url)[member_sudo.partner_id.id]
