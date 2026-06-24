import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";

patch(OrderReceipt, {
    props: {
        ...OrderReceipt.props,
        empty_receipt: { type: Boolean, optional: true },
    },
});

patch(OrderReceipt.prototype, {
    get verificationUrlQrCode() {
        return generateQRCodeDataUrl(this.order.l10n_be_verification_url);
    },
});
