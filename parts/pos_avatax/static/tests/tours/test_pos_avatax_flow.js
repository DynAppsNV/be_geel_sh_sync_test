import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";

registry.category("web_tour.tours").add("test_pos_avatax_flow", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Lumber Inc"),
            ProductScreen.customerIsSelected("Lumber Inc"),
            Chrome.isSynced(),
            ProductScreen.totalAmountIs("5.10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Chrome.isSynced(),
            PaymentScreen.clickPaymentMethod("Cash"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pos_fiscal_position_without_pos_avatax", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A US Partner"),
            ProductScreen.customerIsSelected("A US Partner"),
            ProductScreen.checkFiscalPosition("Default FP"),
            ProductScreen.clickControlButtonMore(),
            Chrome.endTour(),
        ].flat(),
});
