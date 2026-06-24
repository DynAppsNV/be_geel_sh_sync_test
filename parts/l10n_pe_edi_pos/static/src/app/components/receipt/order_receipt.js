import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get peEdiQrcode() {
        if (this.order.l10n_pe_edi_data?.qr_str) {
            return generateQRCodeDataUrl(this.order.l10n_pe_edi_data.qr_str);
        }
        return "";
    },

    get amountToText() {
        return this.order.l10n_pe_edi_data?.amount_to_text;
    },

    get summary() {
        const data = this.order.l10n_pe_edi_data?.qr_str.split("|");
        return data[data.length - 2];
    },
});
