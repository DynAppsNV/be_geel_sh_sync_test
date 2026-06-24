/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Utils from "@point_of_sale/../tests/pos/tours/utils/common";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_settle_account_due", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.settleCustomerAccount("Partner Test 1", "10", "TSJ/", "/00001", true),
            ProductScreen.clickPartnerButton(),
            // Confirm that same invoice shouldn't be in the list again
            PartnerList.settleCustomerAccount(
                "Partner Test 1",
                "10",
                "TSJ/",
                "/00001",
                true,
                false,
                false
            ),
            Dialog.cancel(),
            // On cancelling it will remove customer as well
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.confirmPopup(),
            {
                content: "Receipt doesn't include Empty State",
                trigger: ".pos-receipt:not(:has(i.fa-shopping-cart))",
            },
            ReceiptScreen.isShown(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.containsOrderLine(
                `TSJ/${new Date().getFullYear()}/00001`,
                0,
                "10.00",
                "0.00"
            ),
            ReceiptScreen.receiptAmountTotalIs("0.00"),
            ReceiptScreen.paymentLineContains("Bank", "10.00"),
            ReceiptScreen.paymentLineContains("Customer Account", "-10.00"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("SettleDueButtonPresent", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("A Partner"),
            PartnerList.checkDropDownItemText("Deposit money"),
            PartnerList.clickPartnerOptions("B Partner"),
            PartnerList.checkDropDownItemText("Settle orders"),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_settle_account_due_update_instantly", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // zero price order
            ProductScreen.addOrderline("Desk Pad", "1"),
            Numpad.click("Price"),
            Numpad.isActive("Price"),
            Numpad.click("0"),
            ProductScreen.totalAmountIs("0.0"),
            ProductScreen.clickPayButton(),
            {
                content: "Check that: 'Customer Account' payment method is not available",
                trigger:
                    'body:not(:has(.button.paymentmethod .payment-name:contains("Customer Account")))',
            },
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderline("Desk Pad"),
            Numpad.click("⌫"),
            Numpad.click("⌫"),

            // normal order with due
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Partner"),
            ProductScreen.addOrderline("Desk Pad", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.paymentLineContains("Customer Account", "19.80"),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            PartnerList.settleCustomerAccount(
                "A Partner",
                "19.80",
                "Shop - 000001",
                "",
                false,
                true
            ),
            ProductScreen.clickPartnerButton(),
            // Confirm that same invoice shouldn't be in the list again
            PartnerList.settleCustomerAccount(
                "A Partner",
                "19.80",
                "Shop - 000001",
                "",
                false,
                true,
                false,
                false
            ),
            Dialog.cancel(),
            // On cancelling it will remove customer as well
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Partner"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("1", "0"),
            ProductScreen.totalAmountIs("10.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.confirm("Yes"),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            {
                trigger: "tr:contains('A Partner') .partner-due:contains('9.80')",
            },
            // Settle the rest amount via the open order (9.80 still tied to original order)
            PartnerList.clickPartnerOptions("A Partner"),
            PartnerList.clickDropDownItemText("Settle orders"),
            {
                trigger: "th.o_list_record_selector .form-check-input",
                run: "click",
            },
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.confirm("Yes"),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("A Partner"),
            // Deposit money should be shown (since we have no more due to settle)
            PartnerList.checkDropDownItemText("Deposit money"),
            PartnerList.clickDropDownItemText("Deposit money"),
            Dialog.is("Select the payment method to deposit money"),
            Utils.selectButton("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.bodyIs("You can not deposit zero amount."),
            Dialog.confirm(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_order_partially_backend_01", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Partner"),
            ProductScreen.addOrderline("Desk Pad", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            PartnerList.settleCustomerAccount("A Partner", "19.80", "TSJ/", "/00001", true),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("1", "0"),
            ProductScreen.totalAmountIs("10.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.confirm("Yes"),
            ReceiptScreen.clickNextOrder(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_order_partially_backend_02", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.settleCustomerAccount("A Partner", "4.80", "TSJ/", "/00001", true),
            ProductScreen.totalAmountIs("4.80"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.confirm("Yes"),
            ReceiptScreen.clickNextOrder(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_due_account_ui_coherency_2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("B Partner"),
            negateStep(PartnerList.checkDropDownItemText("Deposit money")),
        ].flat(),
});

registry.category("web_tour.tours").add("SettleDueAmountMoreCustomers", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.searchCustomerValue("BPartner", true),
            {
                trigger: ".partner-line-balance:contains('10.00')",
                run: () => {},
            },
        ].flat(),
});

registry.category("web_tour.tours").add("pos_settle_open_invoice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("C partner"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle invoices')",
                content: "Check the popover opened",
                run: "click",
            },
            {
                trigger: "tr.o_data_row td[name='name']:contains('INV/2025/00001')",
                content: "Check the invoice is present",
                run: "click",
            },
            ProductScreen.clickNumpad("5"),
            ProductScreen.selectedOrderlineHas("INV", 1, "5"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.containsOrderLine("INV/2025/00001", 0, "5.00", "0.00"),
            ReceiptScreen.receiptAmountTotalIs("0.00"),
            ReceiptScreen.paymentLineContains("Bank", "5.00"),
            ReceiptScreen.paymentLineContains("Customer Account", "-5.00"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_settle_open_invoice_with_credit_note", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("C Partner"),
            {
                trigger: "div.o_popover :contains('Settle invoices')",
                content: "Open settle invoices from partner dropdown",
                run: "click",
            },
            {
                trigger: "thead .o_list_record_selector input",
                content: "Click 'Select All' checkbox to select both invoice and credit note",
                run: "click",
            },
            {
                trigger: "tr.o_data_row td[name='name']:contains('INV/2025/00001')",
                content: "Invoice is present in the settle dialog",
            },
            {
                trigger: "tr.o_data_row td[name='name']:contains('RINV/2025/00001')",
                content: "Credit note is present in the settle dialog",
            },
            {
                trigger: ".modal-footer button:contains('Select')",
                content: "Confirm selection of invoice and credit note",
                run: "click",
            },
            ProductScreen.totalAmountIs("8.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),

            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.receiptAmountTotalIs("0.00"),
            ReceiptScreen.paymentLineContains("Bank", "8.00"),
            ReceiptScreen.paymentLineContains("Customer Account", "-8.00"),

            Chrome.endTour(),
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add("test_pos_settling_account_resets_on_payment_screen_unmount", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                {
                    content: "Set the pos_settle_due to True and open payment screen",
                    trigger: "body",
                    run: () => {
                        posmodel.selectedOrder.is_settling_account = true;
                        posmodel.navigate("PaymentScreen", {
                            orderUuid: posmodel.selectedOrderUuid,
                        });
                    },
                },
                PaymentScreen.clickBackToProductScreen(),
                {
                    isActive: ["auto"],
                    content: "Check is_settling_account set to true",
                    trigger: "body",
                    run: () => {
                        const order = posmodel.selectedOrder;
                        if (order.is_settling_account) {
                            throw new Error(
                                "Expected order.is_settling_account to be false, but got true"
                            );
                        }
                    },
                },
                Chrome.endTour(),
            ].flat(),
    });

registry.category("web_tour.tours").add("test_pos_deposit_with_rounding", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("Partner Test 1"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Deposit')",
                content: "Check the popover opened",
                run: "click",
            },
            Utils.selectButton("Cash"),
            PaymentScreen.clickNumpad("1 0 . 0 2"),
            // Cash methods should round the change
            PaymentScreen.changeIs("10.00"),
            PaymentScreen.clickPaymentlineDelButton("Cash", "10.02"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickNumpad("1 0 . 0 2"),
            PaymentScreen.selectedPaymentlineHas("Bank", "10.02"),
            // Non-Cash methods should not round the change
            PaymentScreen.changeIs("10.02"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_account_due_with_refund", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Partner"),
            ProductScreen.addOrderline("Desk Pad", "11"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            // Refund.
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            ProductScreen.clickPartnerButton(),
            {
                trigger: "tr:contains('A Partner') .partner-due:contains('19.80')",
            },
            PartnerList.clickPartnerOptions("A Partner"),
            PartnerList.clickDropDownItemText("Settle orders"),
            {
                trigger: "th.o_list_record_selector .form-check-input",
                run: "click",
            },
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("19.80"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.confirm("Yes"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_settle_open_invoice_child_contact", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("D Contact"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle invoices')",
                content: "Check the popover opened",
                run: "click",
            },
            {
                trigger: `tr.o_data_row td[name='name']:contains('INV/${new Date().getFullYear()}/')`,
                content: "Check the invoice is present",
                run: "click",
            },
            ProductScreen.selectedOrderlineHas("INV", 1, "100"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.receiptAmountTotalIs("0.00"),
            ReceiptScreen.paymentLineContains("Bank", "100.00"),
            ReceiptScreen.paymentLineContains("Customer Account", "-100.00"),
            Chrome.endTour(),
        ].flat(),
});
