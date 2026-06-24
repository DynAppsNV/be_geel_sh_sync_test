/* global posmodel */

import * as BlackboxUtil from "@l10n_be_pos_blackbox/../tests/tours/blackbox_util";
import * as BlackboxOracle from "@l10n_be_pos_blackbox/../tests/tours/blackbox_oracle";
import { registry } from "@web/core/registry";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/utils/split_bill_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Utils from "@point_of_sale/../tests/pos/tours/utils/common";
import * as CashMoveList from "@point_of_sale/../tests/pos/tours/utils/cash_move_list_util";
import { run } from "@point_of_sale/../tests/generic_helpers/utils";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("l10n_be_pos_blackbox_sign_sale_refund_tour", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Pay an order
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData(),
            BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 1 }),
            // Do a refund of the previous order
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Active"),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.totalIs("-2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData("VAT TICKET REFUND"),
            BlackboxOracle.checkBlackboxRequestCounter({ M111_signSale_Refund: 1 }),
            // Check signOrder when saving an order
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            Chrome.clickPlanButton(),
            BlackboxOracle.checkBlackboxRequestCounter({ M121_signOrder: 1 }),
            // Pay the order
            FloorScreen.clickTable("2"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.totalIs("4.40"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData(),
            BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 1 }),
            // Partially refund the order (only one Coca-Cola)
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0003"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.totalIs("-2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData("VAT TICKET REFUND"),
            BlackboxOracle.checkBlackboxRequestCounter({ M112_signSale_RefundPartial: 1 }),
            BlackboxUtil.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_be_pos_blackbox_sign_sale_invoice_tour", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Pay an order
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A blackbox partner"),
            BlackboxOracle.checkBlackboxRequestCounter({
                M121_signOrder: 1,
                M122_signCostCenterChange: 1,
            }),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData(),
            FloorScreen.isShown(),
            BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 1, M150_signInvoice: 1 }),
            BlackboxUtil.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_l10n_be_pos_blackbox_sign_sale_backend_offline", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Cut the connection to the backend (simulate offline, but we can still reach the blackbox)
            BlackboxUtil.setCannotReachBackend(),
            // Try to make an order while offline
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            run(() => {
                const order = posmodel.getOrder();
                if (order.isSynced || !order.isDirty()) {
                    throw new Error("The order should be unsynced and dirty while offline");
                }
            }, "Check that the order is dirty and unsynced"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.confirm("Continue with limited functionality"),
            BlackboxUtil.receiptContainsBlackboxData(),
            BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 1 }),
            // Restore the connection to the backend, in order to sync the offline order
            BlackboxUtil.setCanReachBackend(),
            Chrome.isSynced(),
            BlackboxUtil.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_l10n_be_pos_blackbox_sign_sale_blackbox_offline", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Cut the connection to the blackbox
            BlackboxUtil.setCannotReachBlackbox(),
            // Try to make an order while offline
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            // Since the blackbox is unreachable, the order cannot be signed
            BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 0 }),
            BlackboxUtil.confirmFdmErrorDialog(),
            Chrome.clickPlanButton(),
            BlackboxUtil.setCanReachBlackbox(),
            BlackboxUtil.endTour(),
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add("test_l10n_be_pos_blackbox_sign_sale_backend_offline_blackbox_offline", {
        steps: () =>
            [
                BlackboxUtil.startPosBlackbox(),
                // Test automatic work-in
                BlackboxUtil.checkUserClockInStatus(),
                BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
                // Cut the connection to the backend and to the blackbox
                BlackboxUtil.setCannotReachBackend(),
                BlackboxUtil.setCannotReachBlackbox(),
                // Try to make an order while offline
                FloorScreen.clickTable("5"),
                ProductScreen.clickDisplayedProduct("Coca-Cola"),
                ProductScreen.totalAmountIs("2.20"),
                ProductScreen.clickPayButton(false),
                ProductScreen.discardOrderWarningDialog(),
                PaymentScreen.emptyPaymentlines("2.20"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickValidate(),
                BlackboxUtil.confirmFdmErrorDialog(),
                // Since the blackbox is unreachable, the order cannot be signed
                BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 0 }),
                BlackboxUtil.setCanReachBackend(),
                BlackboxUtil.setCanReachBlackbox(),
                BlackboxUtil.endTour(),
            ].flat(),
    });

registry.category("web_tour.tours").add("l10n_be_pos_blackbox_transfer_tour", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Add lines to a table and transfer it to an empty table
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            // Sync the order
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            BlackboxOracle.checkBlackboxRequestCounter({ M121_signOrder: 1 }),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            BlackboxOracle.checkBlackboxRequestCounter({ M122_signCostCenterChange: 1 }),
            ProductScreen.totalAmountIs("2.20"),
            // Create a new order and transfer it to the existing order
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("2.20"),
            // Sync the order
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.totalAmountIs("4.40"),
            // Create a new order and merge it with the existing order
            Chrome.clickPlanButton(),
            Chrome.waitRequest(),
            BlackboxOracle.checkBlackboxRequestCounter({
                M122_signCostCenterChange: 1,
                M121_signOrder: 1,
            }),
            FloorScreen.clickTable("2"),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            Chrome.clickPlanButton(),
            FloorScreen.linkTables("2", "4"),
            FloorScreen.clickTable("4"),
            Chrome.waitRequest(),
            BlackboxOracle.checkBlackboxRequestCounter({
                M122_signCostCenterChange: 1,
                M121_signOrder: 1,
            }),
            // Pay the order
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.totalIs("6.60"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData(),
            BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 1 }),
            BlackboxUtil.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_be_pos_blackbox_split_table_tour", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Make an order on table 5
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.totalAmountIs("8.80"),
            // Sync the order
            Chrome.clickPlanButton(),
            BlackboxOracle.checkBlackboxRequestCounter({ M121_signOrder: 1 }),
            FloorScreen.clickTable("5"),
            // Split "Water" from the order
            ProductScreen.clickControlButton("Split"),
            SplitBillScreen.clickOrderline("Water"),
            // Transfer "Water" to a new table (table 4)
            SplitBillScreen.clickButton("Transfer"),
            FloorScreen.clickTable("4"),
            BlackboxOracle.checkBlackboxRequestCounter({
                M122_signCostCenterChange: 2, // one for the split, one for the transfer
            }),
            ProductScreen.totalAmountIs("2.20"),
            // Sync the order
            Chrome.clickPlanButton(),
            // Split "Coca-Cola" from order on table 5 and pay it directly
            FloorScreen.clickTable("5"),
            ProductScreen.clickControlButton("Split"),
            SplitBillScreen.clickOrderline("Coca-Cola"),
            SplitBillScreen.clickButton("Pay"),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.totalIs("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData(),
            BlackboxOracle.checkBlackboxRequestCounter({
                M110_signSale: 1,
                M122_signCostCenterChange: 1,
            }),
            // Split "Minute Maid" from order, add a line and pay it
            SplitBillScreen.clickOrderline("Minute Maid"),
            SplitBillScreen.clickButton("Split Order"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData(),
            BlackboxOracle.checkBlackboxRequestCounter({
                M110_signSale: 1,
                M122_signCostCenterChange: 1,
                M121_signOrder: 1,
            }),
            BlackboxUtil.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_be_pos_blackbox_cash_move_cancel_order_tour", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Make an order on table 5
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            // Sync the order
            Chrome.clickPlanButton(),
            BlackboxOracle.checkBlackboxRequestCounter({ M121_signOrder: 1 }),
            // Cancel the order
            FloorScreen.clickTable("5"),
            ProductScreen.clickControlButton("Cancel Order"),
            Dialog.confirm(),
            Dialog.is({ title: "Printing Failed" }),
            Dialog.cancel(),
            // Now do cash moves
            Chrome.doCashMove("10", "Cash in reason"),
            Chrome.clickMenuOption("Cash In/Out"),
            Utils.selectButton("Details"),
            CashMoveList.checkNumberOfRows(1),
            CashMoveList.checkCashMoveShown("10"),
            BlackboxOracle.checkBlackboxRequestCounter({
                M110_signSale: 1,
                M121_signOrder: 1,
                M130_signMoneyInOut: 1,
            }),
            BlackboxUtil.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_be_pos_blackbox_be_close_session_z_reports", {
    steps: () =>
        [
            BlackboxUtil.startPosBlackbox(),
            // Test automatic work-in
            BlackboxUtil.checkUserClockInStatus(),
            BlackboxOracle.checkBlackboxRequestCounter({ M140_signWorkIn: 1 }),
            // Pay an order
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            BlackboxUtil.receiptContainsBlackboxData(),
            BlackboxOracle.checkBlackboxRequestCounter({ M110_signSale: 1 }),
            // Close the register (it should generate Z reports and sign them)
            Chrome.clickMenuOption("Close Register"),
            {
                trigger: ".modal .modal-footer .btn:contains(close register)",
                run: "click",
                expectUnloadPage: true,
            },
            BlackboxUtil.endTour(),
        ].flat(),
});
