import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        if (!this.pos.blackbox.isActive) {
            return buttons;
        }
        const orderline = this.currentOrder.getSelectedOrderline();
        // When the selected orderline is a discount line, all numpad buttons should be disabled
        // If the user wants to edit the discount, they should use the discount control button
        // We avoid having inconsistent states where (discount amount != discountPc * orderPrice, that could cause issue when sending amount to the FDM
        if (orderline?.isDiscountLine) {
            buttons.forEach((button) => {
                button.disabled = true;
            });
        }
        return buttons;
    },
});
