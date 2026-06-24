import { patch } from "@web/core/utils/patch";
import { WebsiteSale } from "@website_sale/interactions/website_sale";

/**
 * Update the max quantity when the renting constraints change or when the dates change
 */
patch(WebsiteSale.prototype, {
    onRentingConstraintsChanged(event) {
        super.onRentingConstraintsChanged(event);
        this.setAddQtyInputMax();
    },

    onDatePickerApply(event) {
        super.onDatePickerApply(event);
        this.setAddQtyInputMax();
    },

    setAddQtyInputMax() {
        const addQtyInput = this.el.querySelector("input[name='add_qty']");
        if (this.rentingAvailabilities && addQtyInput) {
            const productId = this._getProductId(this.el);
            const { start_date, end_date } = this._getRentingDates(this.el);
            const qty = parseFloat(addQtyInput.value) || 1;
            let availableQty = Infinity;
            for (const interval of this.rentingAvailabilities[productId]) {
                if (interval.start < end_date) {
                    if (interval.end > start_date) {
                        availableQty = Math.min(interval.quantity_available, availableQty);
                    }
                } else {
                    break;
                }
            }
            addQtyInput.dataset.max = availableQty || 1;
            if (qty > availableQty) {
                addQtyInput.value = addQtyInput.dataset.max;
            }
        }
    },
});
