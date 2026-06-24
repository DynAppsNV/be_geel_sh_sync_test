from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        """Put automated action into code: Send mail upon creation payment"""
        payments = super()._create_payments()

        for payment in payments.filtered(
            lambda p: p.invoice_ids and p.state in ("in_process", "paid")
        ):
            template = self.env.ref(
                "account.mail_template_data_payment_receipt", raise_if_not_found=False
            )
            if template:
                template.send_mail(payment.id, force_send=True)
        return payments
