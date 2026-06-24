import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async _fetchUrbanpiperOrderCount(order_id) {
        await super._fetchUrbanpiperOrderCount(...arguments);
        const order = this.models["pos.order"].get(order_id);
        if (this.blackbox.isActive && order) {
            if (
                !order.l10n_be_short_signature &&
                order.state === "paid" &&
                ["food_ready", "dispatched", "completed"].includes(order.delivery_status)
            ) {
                await this.signExternalOrder(order);
            }
        }
    },
});
