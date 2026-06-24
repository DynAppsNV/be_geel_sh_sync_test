import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";
import { patch } from "@web/core/utils/patch";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

patch(InputGenerator.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.settleDueLines = this.order?.lines.filter((line) => line.isAnySettleLine());
        this.settleDueTotal = this.settleDueLines?.length
            ? Math.abs(this.settleDueLines.reduce((total, line) => total + line.price_unit, 0))
            : 0;
    },
    generatePriceChangeInput(line, initPrice, { priceUnit, discount, globalDiscount, qty }) {
        if (line.isAnySettleLine()) {
            return [];
        }
        return super.generatePriceChangeInput(...arguments);
    },

    generateLineVatInput(line, { priceUnit, discount, globalDiscount, qty }) {
        if (line.isAnySettleLine()) {
            return [
                this.generateTaxVatInput(
                    line,
                    "X",
                    roundCurrency(line.price_unit, line.order_id.currency),
                    { priceUnit, discount, globalDiscount, qty }
                ),
            ];
        }
        return super.generateLineVatInput(...arguments);
    },
    generateProductInput(line, { priceUnit, discount, globalDiscount, qty }) {
        const res = super.generateProductInput(...arguments);
        if (line.isAnySettleLine()) {
            res.quantity = 1;
            res.unitPrice = roundCurrency(line.price_unit, line.order_id.currency);
        }
        return res;
    },
    generatePaymentLineInput(payment) {
        const res = super.generatePaymentLineInput(...arguments);
        if (payment.payment_method_id.type === "pay_later") {
            if (res.amount < 0) {
                return;
            }
        }
        return res;
    },
    getTransactionLineTotal(line, qty) {
        if (line.isAnySettleLine()) {
            return roundCurrency(line.price_unit, line.order_id.currency);
        }
        return super.getTransactionLineTotal(...arguments);
    },
    getTransactionTotal() {
        const total = super.getTransactionTotal(...arguments);
        return roundCurrency(total + this.settleDueTotal, this.order.currency);
    },
});
