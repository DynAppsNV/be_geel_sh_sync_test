import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get l10n_co_edi_pos_receipt_data() {
        const receiptData = this.order.l10n_co_edi_pos_receipt_data;

        if (receiptData) {
            return JSON.parse(receiptData);
        } else {
            return undefined;
        }
    },
});
