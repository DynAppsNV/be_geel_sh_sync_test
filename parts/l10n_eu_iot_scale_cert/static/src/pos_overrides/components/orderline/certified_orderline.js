import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    //@override
    get lineScreenValues() {
        const vals = super.lineScreenValues;
        const line = this.line;
        const priceUnit = `${line.currencyDisplayPriceUnit} / ${
            line.product_id?.uom_id?.name || ""
        }`;
        // "showPrice" condition is removed to always display the price per unit
        vals.displayPriceUnit = line.price !== 0 && priceUnit;
        return vals;
    },
});
