import { ActionScreen } from "@point_of_sale/app/screens/action_screen";
import { useEffect } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { patch } from "@web/core/utils/patch";

patch(ActionScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();

        useEffect(
            (actionName) => {
                if (actionName === "manage-booking") {
                    this.pos.data
                        .call("calendar.event", "action_open_booking_gantt_view", [false], {
                            context: {
                                appointment_type_id: this.pos.config.raw.appointment_type_id,
                            },
                        })
                        .then((result) => {
                            this.pos.action.doAction(result);
                        });
                }
            },
            () => [this.props.actionName]
        );
    },
});
