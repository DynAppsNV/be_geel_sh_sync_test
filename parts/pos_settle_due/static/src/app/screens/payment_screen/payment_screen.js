import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { floatIsZero } from "@web/core/utils/numbers";
import { onWillUnmount } from "@odoo/owl";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

patch(PaymentScreen, {
    props: {
        ...PaymentScreen.props,
        isDepositOrder: { type: Boolean, optional: true },
    },
});

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        const order = this.currentOrder;
        const settleLines = order.lines.filter(
            (line) => line.isSettleDueLine() || line.isSettleInvoiceLine()
        );
        if (
            settleLines.length ||
            order.is_settling_account ||
            floatIsZero(order.totalDue, this.pos.currency.decimal_places)
        ) {
            this.payment_methods_from_config = this.payment_methods_from_config.filter(
                (pm) => pm.type !== "pay_later"
            );
        }
        onWillUnmount(this.onUnmount);
    },

    onUnmount() {
        /*
         * When the settlement payment selection dialog is opened,
         * `is_settling_account` is temporarily set to true.
         *
         * However, if the user exits the settlement process
         * (without completing the payment) and returns to the previous screen,
         * we must reset this flag to false.
         *
         * Failing to do so allows the same order to be used for
         * non-settlement operations, which can cause inconsistencies—
         * particularly in cases where invoices are mandatory
         * for all payments except settlements.
         */
        if (this.currentOrder?.is_settling_account && this.currentOrder.state !== "paid") {
            this.currentOrder.is_settling_account = false;
        }
    },

    toggleIsToInvoice() {
        if (
            !this.currentOrder.isToInvoice() &&
            this.currentOrder.is_settling_account &&
            this.currentOrder.lines.length === 0
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Empty Order"),
                body: _t("Empty orders cannot be invoiced."),
            });
        } else {
            super.toggleIsToInvoice();
        }
    },
    get partnerInfos() {
        const order = this.currentOrder;
        return this.pos.getPartnerCredit(order.getPartner());
    },
    get highlightPartnerBtn() {
        const order = this.currentOrder;
        const partner = order.getPartner();
        return (!this.partnerInfos.useLimit && partner) || (!this.partnerInfos.overDue && partner);
    },
    // TODO: TO BE REMOVED IN MASTER
    async ensurePartnerSelected(order) {
        const validation = new OrderPaymentValidation({
            pos: this.pos,
            orderUuid: order.uuid,
        });
        return await validation.ensurePartnerSelected();
    },
    // TODO: TO BE REMOVED IN MASTER
    async validateOrder(isForceValidate) {
        const validation = new OrderPaymentValidation({
            pos: this.pos,
            orderUuid: this.currentOrder.uuid,
        });
        return await validation.validateOrder(isForceValidate);
    },
    // TODO: TO BE REMOVED IN MASTER
    async settleOrderDues(order, partner, paylaterPaymentMethod, settleLines) {
        const validation = new OrderPaymentValidation({
            pos: this.pos,
            orderUuid: order.uuid,
        });
        return await validation.settleOrderDues(partner, paylaterPaymentMethod, settleLines);
    },
    // TODO: TO BE REMOVED IN MASTER
    async depositOrder(order, partner, change, paylaterPaymentMethod) {
        const validation = new OrderPaymentValidation({
            pos: this.pos,
            orderUuid: order.uuid,
        });
        return await validation.depositOrder(partner, change, paylaterPaymentMethod);
    },
    getLineToRemove() {
        return this.currentOrder.lines.filter(
            (line) =>
                line.product_id.uom_id.isZero(line.qty) &&
                !line.isSettleDueLine() &&
                !line.isSettleInvoiceLine()
        );
    },
});
