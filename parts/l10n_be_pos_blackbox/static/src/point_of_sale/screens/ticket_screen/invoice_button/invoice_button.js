import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(InvoiceButton.prototype, {
    setup() {
        super.setup(...arguments);
        this.wasAlreadyInvoiced = this.isAlreadyInvoiced;
    },
    async _invoiceOrder() {
        if (this.pos.blackbox.isActive && this.isAlreadyInvoiced) {
            await this.pos.blackbox.signCopy.signInvoice(
                this.props.order,
                this.pos.getCashier().l10n_be_insz_or_bis_number
            );
        }
        return await super._invoiceOrder(...arguments);
    },
    async onWillInvoiceOrder(order, partner) {
        if (this.pos.blackbox.isActive) {
            if (!partner.vat) {
                this.dialog.add(AlertDialog, {
                    title: _t("VAT Number Required"),
                    body: _t(
                        "A VAT number is required to invoice an order. Please set a VAT number for the customer."
                    ),
                });
                return false;
            }
        }
        return await super.onWillInvoiceOrder(...arguments);
    },
    async _downloadInvoice(orderId) {
        const order = await super._downloadInvoice(orderId);
        if (this.pos.blackbox.isActive && order && !this.wasAlreadyInvoiced) {
            await this.pos.blackbox.signInvoice.sign(
                this.props.order,
                this.pos.getCashier().l10n_be_insz_or_bis_number
            );
        }
        return order;
    },
});
