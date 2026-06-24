# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_pdf_raw(self):
        self.ensure_one()
        if pdf_raw := super()._get_pdf_raw():
            return pdf_raw

        document = self.document_ids.filtered('has_embedded_pdf')[:1]
        return document._extract_pdf_from_xml() if document else False

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for vals, attachment in zip(vals_list, attachments):
            if vals.get('res_model') != 'account.move':
                continue
            move = self.env['account.move'].browse(vals.get('res_id', False))
            # In order to avoid creation of extra documents we retrict creation of a document to:
            # - attachments of a misc operation
            # - xml file after it has been succesfully registered as move attachment
            # Only in the case where the 'no_document' flag is set to False
            if (
                not self.env.context.get('no_document')
                and (
                    move.move_type == 'entry'
                    or attachment.mimetype in ('application/xml', 'text/xml')
                )
            ):
                move._update_or_create_document(attachment.id)
        return attachments

    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get('no_document'):
            return res

        res_model = vals.get('res_model')

        if res_model == 'account.move':
            valid_moves = self.env['account.move'].search([
                ('id', 'in', self.mapped('res_id')),
                ('move_type', '=', 'entry')
            ])
            for attachment in self.filtered(
                lambda a: a.res_id and (a.res_id in valid_moves.ids or a.mimetype in ('application/xml', 'text/xml'))
            ):
                move = self.env['account.move'].browse(attachment.res_id)
                move._update_or_create_document(attachment.id)

        return res
