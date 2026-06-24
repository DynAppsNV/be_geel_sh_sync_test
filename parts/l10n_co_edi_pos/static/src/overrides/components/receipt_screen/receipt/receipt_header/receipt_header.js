import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { patch } from "@web/core/utils/patch";

patch(ReceiptHeader.prototype, {
    get l10n_co_edi_pos_header_data() {
        const receiptData = this.order.l10n_co_edi_pos_receipt_data;

        if (receiptData) {
            return JSON.parse(receiptData).header;
        } else {
            return undefined;
        }
    },
});
