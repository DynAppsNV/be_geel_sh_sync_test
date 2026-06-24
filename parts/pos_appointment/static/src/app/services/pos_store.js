import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async manageBookings() {
        this.orderToTransferUuid = null;
        this.navigate("ActionScreen", { actionName: "manage-booking" });
    },
    async editBooking(appointment) {
        const action = await this.data.call("calendar.event", "action_open_booking_form_view", [
            appointment.id,
        ]);
        return this.action.doAction(action);
    },
});
