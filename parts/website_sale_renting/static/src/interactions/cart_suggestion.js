import { patch } from '@web/core/utils/patch';
import { CartSuggestion } from '@website_sale/interactions/cart_suggestion';

patch(CartSuggestion.prototype, {
    /**
     * @param {Event} ev
     */
    addSuggestedProduct(ev) {
        const dataset = ev.currentTarget.dataset;

        this.services["cart"].add(
            {
                productTemplateId: parseInt(dataset.productTemplateId),
                productId: parseInt(dataset.productId),
                isCombo: dataset.productType === 'combo',
                start_date: dataset.rentalStartDate,
                end_date: dataset.rentalReturnDate,
            },
            {
                isBuyNow: true,
                showQuantity: Boolean(dataset.showQuantity),
            }
        );
    },
});
