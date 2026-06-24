/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Notification from "@point_of_sale/../tests/generic_helpers/notification_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as UrbanPiper from "@pos_urban_piper/../tests/tours/utils/pos_urban_piper_utils";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_pos_urbanpiper_future_delivery_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            UrbanPiper.fetchDeliveryData(),
            UrbanPiper.checkNewOrderCount(1),
            UrbanPiper.onDropdownStatus("New"),
            TicketScreen.selectOrder("001"),
            inLeftSide({
                content: "Check if delivery order is a future order",
                trigger: ".leftpane div:contains(This order is scheduled order.)",
            }),
            UrbanPiper.orderButtonClick("Accept"),
            UrbanPiper.fetchDeliveryData(),
            {
                content: "Trigger future order preparation notification",
                trigger: "body",
                run: async () => {
                    await posmodel.data.call("pos.order", "notify_future_deliveries");
                },
            },
            Notification.has("Scheduled Order"),
            UrbanPiper.checkNewOrderCount(0),
            UrbanPiper.orderHasText("001", "Acknowledged"),
        ].flat(),
});
