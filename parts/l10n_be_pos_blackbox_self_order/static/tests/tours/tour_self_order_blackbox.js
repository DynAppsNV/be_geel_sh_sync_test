/* global posmodel */

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as BlackboxOracle from "@l10n_be_pos_blackbox/../tests/tours/blackbox_oracle";
import { run } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("test_l10n_be_pos_blackbox_kiosk_tour", {
    steps: () => [
        BlackboxOracle.enableBlackboxOracle(),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
        ProductPage.clickProduct("Test Product"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 1 }),
        run(async () => {
            posmodel.currentOrder.nb_print = 0;
            await BlackboxOracle.generateAndCheckTicket(posmodel.currentOrder);
        }, "Check the Kiosk receipt after signing the order"),
        run(async () => {
            await posmodel.handleKioskSessionStatusChange("closed");
        }, "Close the session"),
        BlackboxOracle.disableBlackboxOracle(),
    ],
});
