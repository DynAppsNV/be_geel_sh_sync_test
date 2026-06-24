import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    initState() {
        super.initState();
        this.uiState.maxQuantity = this.qty;
        this.uiState.maxUnitPrice = undefined;
    },
    resetMaxValues() {
        this.uiState.maxQuantity = this.qty;
        this.uiState.maxUnitPrice = this.blackboxPriceUnitNoDiscount;
    },
    /**
     * IMPORTANT NOTES:
     *  we must make sure that we always send price including taxes to the blackbox,
     *  the POS should compute prices including taxes, no matter the configuration of the taxes (price included or not).
     *
     * In a tax included / excluded context, we should ensure these properties:
     * - For each transactionLine:
     *     - transactionLine.lineTotal == Sum(vat.price + Sum(priceChange.amount)) over all VAT objects of the product.
     * - For the whole transaction:
     *    - transactionTotal == Sum(transactionLine.lineTotal)
     *
     *  Otherwise the blackbox will reject the transaction, and we won't be able to sign the order.
     *  And the idea is that these properties should still be true with every type of price changes (line discount, global discount, manual price change, loyalty,... etc.).
     */

    /**
     * Compute a Blackbox-compatible line total.
     *
     * Context:
     * Odoo applies global rounding (`round_globally`) when computing taxes. This can
     * lead to systematic discrepancies between:
     *
     *   - The globally rounded total including taxes
     *   - The line total computed as (quantity × unit price including taxes)
     *
     * Example: (see first test inside 'input_generator.test.js')
     * Create an order line with sale price 3.34 (including 12% tax) and quantity 7.
     *   - 7 × 3.34 (price incl. 12% tax) = 23.38 (globally rounded total) => order total which is correct
     *   - Line computation: 7 × 3.34 = 23.39 => line total (displayed in the UI) which is incorrect because it miss 'delta_total_included_currency'
     *
     * This rounding mismatch exists throughout Odoo (sale, invoice, POS, etc.).
     * However, in POS it becomes critical because the fiscal blackbox requires
     * *exact* numerical consistency. Any mismatch causes the transaction to be
     * rejected and prevents signing the sale.
     *
     * Blackbox error example:
     *   "Value error, lineTotal mismatch for SINGLE_PRODUCT
     *    (expected 23.38, got 23.39)"
     *
     * This effectively yields the equivalent of:
     *   total_included_currency + delta_total_included_currency
     *
     * Notes:
     * - Combo lines still use `displayPrice`, maybe we will have same issue with combo later?
     */

    /**
     * Line price including:
     * - Taxes
     * - Discount line (not global)
     */
    get blackboxPrice() {
        if (this.combo_line_ids.length) {
            return this.combo_line_ids.reduce((sum, line) => sum + line.blackboxPrice, 0);
        }
        return this.currency.round(this.prices.total_included_currency);
    },

    /**
     * Unit price including:
     * - Taxes
     * - Discount line (not global)
     */
    get blackboxPriceUnit() {
        const childLinesPrice = this.combo_line_ids.reduce(
            (acc, line) => acc + line.displayPriceUnitIncl,
            0
        );
        const price = this.combo_line_ids.length ? childLinesPrice : this.displayPriceUnitIncl;
        return this.currency.round(price);
    },

    /**
     * Unit price including:
     * - Taxes
     */
    get blackboxPriceUnitNoDiscount() {
        const childLinesPrice = this.combo_line_ids.reduce(
            (acc, line) => acc + line.priceUnitInclNoDiscount,
            0
        );

        const price = this.combo_line_ids.length ? childLinesPrice : this.priceUnitInclNoDiscount;
        return this.currency.round(price);
    },

    /**
     *  This is the unit price including taxes used for blackbox.
     *  this should return the price including taxes for quantity = 1
     */
    get blackboxProductProductPrice() {
        return this.currency.round(this.product_id.getTaxDetails().total_included);
    },

    /**
     * The three next overrides are meant to keep track of changes before paying the order.
     * If before paying, the max quantity or unit price is bigger than the current value,
     * we should sign a correction.
     */
    setQuantity(quantity, keep_price) {
        const res = super.setQuantity(...arguments);
        if (res === true) {
            if (this.order_id.preset_id?.is_return) {
                quantity = -Math.abs(quantity);
            }

            const quant =
                typeof quantity === "number"
                    ? quantity
                    : parseFloat("" + (quantity ? quantity : 0));
            const line = this.combo_parent_id ? this.combo_parent_id : this;
            if (quant > line.uiState.maxQuantity || !line.uiState.maxQuantity) {
                line.uiState.maxQuantity = quant;
            }
        }
        return res;
    },
    setUnitPrice(price) {
        // We set the maxUnitPrice here because we wanna know what was the unit price before
        // the change if it was not already set. It cannot be set in initState because it depends
        // on the price that is computed in pos_order_accounting.js later in the flow.
        if (!this.uiState.maxUnitPrice) {
            this.uiState.maxUnitPrice = this.blackboxPriceUnitNoDiscount;
        }
        super.setUnitPrice(...arguments);
        if (this.blackboxPriceUnitNoDiscount > this.uiState.maxUnitPrice) {
            this.uiState.maxUnitPrice = this.blackboxPriceUnitNoDiscount;
        }
    },
});
