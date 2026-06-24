import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

patch(PosOrder.prototype, {
    initState() {
        super.initState(...arguments);
        this.uiState.deletedLines = {};
    },
    get isPartialRefund() {
        if (!this.isRefund) {
            return false;
        }

        const refundLine = this.lines.find((l) => l.refunded_orderline_id?.order_id);
        if (!refundLine) {
            return false;
        }

        const refundedOrder = this.refunded_order_id;
        return refundedOrder && Math.abs(refundedOrder.priceIncl) !== Math.abs(this.priceIncl);
    },
    // Orders from mobile that are paid online, have 'nb_print = 1' before being printed the first time
    // (see 'get_order_to_print' inside 'pos_online_payment_self_order/pos_order.py')
    get isCopyTicket() {
        return this.source == "mobile" ? this.nb_print > 1 : this.nb_print > 0;
    },
    get isSigned() {
        return this.l10n_be_short_signature && this.finalized;
    },
    get orderTypeBlackbox() {
        let type = "PRO FORMA";

        if (this.isSigned || this.uiState.isEmptyReceipt) {
            type = "N";
        }

        if (this.isRefund && this.isSigned) {
            type = "N REFUND";
        }

        if (this.isCopyTicket && this.isSigned) {
            type = "COPY";
        }

        if (this.config.l10n_be_training_mode) {
            type = "T";
        }

        return type;
    },

    get orderTypeStringBlackbox() {
        switch (this.orderTypeBlackbox) {
            case "N":
                return _t("VAT TICKET");
            case "N REFUND":
                return _t("VAT TICKET REFUND");
            case "COPY":
                return _t("COPY TICKET");
            case "PRO FORMA":
                return _t("PROVISIONAL BILL");
            default:
                return _t("THIS IS NOT A VAT TICKET");
        }
    },
    get generateTransactionLines() {
        const generator = new InputGenerator({
            models: this.models,
            order: this,
        });
        return generator.generateTransactionLinesInput();
    },
    updateLastTransactionLines() {
        this.l10n_be_last_transaction_by_line = this.generateTransactionLines;
    },
    generateCostCenterInput() {
        const customer = this.partner_id;
        const table = this.table_id;
        const orderUuid = this.uuid;

        const type = this.getCostCenterType(customer, table);

        const id = customer
            ? `${customer.id} ${customer.name}`
            : table?.table_number
            ? table.table_number.toString()
            : this.getName();

        const reference = customer?.vat ? customer.vat.toString() : orderUuid?.toString();

        return { id, type, reference };
    },
    getCostCenterType(customer, table) {
        if (customer) {
            return "CUSTOMER";
        } else if (this.source == "kiosk") {
            return "KIOSK";
        } else if (this.source == "mobile") {
            return "WEBSHOP";
        } else if (table) {
            return "TABLE";
        } else {
            return "ON_HOLD";
        }
    },
    /* Get the order lines for which we want to generate transaction lines input
     *   - We never want to include global discount lines
     *   _ We don't send line with 0 quantity
     *   - Tip line:
     *      - Included only for refund orders (to refund the tip)
     *      - Excluded for normal orders (as tip is handled as a separate payment line)
     */
    get linesSendableToBlackbox() {
        return this.refunded_order_id
            ? this.lines.filter((line) => !line.isGlobalDiscountLine() && line.qty != 0)
            : this.lines.filter(
                  (line) => !line.isTipLine() && !line.isGlobalDiscountLine() && line.qty != 0
              );
    },
    removeOrderline(line) {
        let initialTransLine = null;
        const lineToCheck = line.combo_parent_id ? line.combo_parent_id : line;
        const lastSigned = this.l10n_be_last_transaction_by_line;
        const wasSigned = !!(lineToCheck?.uuid && lastSigned?.[lineToCheck.uuid]);
        if (lineToCheck && !wasSigned) {
            const generator = new InputGenerator({
                models: lineToCheck.order_id.models,
                order: lineToCheck.order_id,
                inszOrBisNumber: this.models["res.users"].getFirst().l10n_be_insz_or_bis_number,
            });
            initialTransLine = generator.generateTransactionLine(lineToCheck, {
                qty: lineToCheck.uiState.maxQuantity || lineToCheck.qty,
            });
            initialTransLine.lineTotal = generator.computeTransactionLineTotal(initialTransLine);
        }
        this.uiState.deletedLines[lineToCheck.uuid] = initialTransLine;
        return super.removeOrderline(...arguments);
    },
    resetDeletedLines() {
        this.uiState.deletedLines = {};
    },
});
