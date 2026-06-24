import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async _doneOrder(order) {
        await super._doneOrder(...arguments);
        if (this.pos.blackbox.isActive) {
            order = this.pos.models["pos.order"].get(order.id);
            if (
                !order.l10n_be_short_signature &&
                order?.state === "paid" &&
                order.delivery_status === "food_ready"
            ) {
                await this.pos.signExternalOrder(order);
            }
        }
    },
});
