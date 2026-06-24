import { PosOrderAccounting } from "@point_of_sale/app/models/accounting/pos_order_accounting";
import { patch } from "@web/core/utils/patch";

patch(PosOrderAccounting.prototype, {
    get shouldRoundChange() {
        if (!this.is_settling_account) {
            return super.shouldRoundChange;
        }

        return this.orderIsRounded;
    },
});
