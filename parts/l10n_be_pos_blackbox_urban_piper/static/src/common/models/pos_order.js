import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    getCostCenterType(customer, table) {
        if (this.delivery_provider_id) {
            return "PLATFORM";
        }
        return super.getCostCenterType(...arguments);
    },
});
