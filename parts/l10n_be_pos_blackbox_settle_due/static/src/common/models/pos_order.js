import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get linesSendableToBlackbox() {
        const lines = super.linesSendableToBlackbox;
        const settleLines = this.lines.filter((line) => line.isAnySettleLine() && line.qty == 0);
        return [...lines, ...settleLines];
    },
});
