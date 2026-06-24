import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(OrderPaymentValidation.prototype, {
    async afterOrderValidation(suggestToSync = false) {
        await super.afterOrderValidation(...arguments);
        const hasCustomerAccountAsPaymentMethod = this.order.payment_ids.find(
            (paymentline) => paymentline.payment_method_id.type === "pay_later"
        );
        const partner = this.order.getPartner();
        if (hasCustomerAccountAsPaymentMethod && partner.total_due !== undefined) {
            this.pos.refreshTotalDueOfPartner(partner);
        }
    },
    async validateOrder(isForceValidate) {
        const order = this.order;
        const change = -order.change;
        const settleLines = order.lines.filter(
            (line) => line.isSettleDueLine() || line.isSettleInvoiceLine()
        );
        const paylaterPaymentMethod = this.pos.models["pos.payment.method"].find(
            (pm) =>
                this.pos.config.payment_method_ids.some((m) => m.id === pm.id) &&
                pm.type === "pay_later"
        );
        const existingPayLaterPayment = order.payment_ids.find(
            (payment) => payment.payment_method_id.type == "pay_later"
        );

        // If the user attempts to deposit a zero amount
        if (this.isDepositOrder && this.pos.currency.isZero(change) && order.isEmpty()) {
            return this.pos.dialog.add(AlertDialog, {
                title: _t("The order is empty"),
                body: _t("You can not deposit zero amount."),
            });
        }

        //If it's a deposit or settle due order
        if (
            ((!this.pos.currency.isZero(change) &&
                order.getOrderlines().length === 0 &&
                this.isDepositOrder) ||
                settleLines.length) &&
            paylaterPaymentMethod &&
            !existingPayLaterPayment
        ) {
            if (order.isRefund) {
                return this.pos.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("You cannot refund a deposit/settling order."),
                });
            }
            const partner = await this.ensurePartnerSelected();
            if (!partner) {
                return;
            }
            if (settleLines.length) {
                return this.settleOrderDues(partner, paylaterPaymentMethod, settleLines);
            } else {
                return this.depositOrder(partner, change, paylaterPaymentMethod);
            }
        } else {
            return super.validateOrder(...arguments);
        }
    },
    get isDepositOrder() {
        return this.order.is_settling_account;
    },
    async ensurePartnerSelected() {
        let partner = this.order.getPartner();
        if (!partner) {
            const confirmed = await ask(this.pos.dialog, {
                title: _t("The order is empty"),
                body: _t(
                    "Do you want to deposit money to a specific customer? If so, first select him/her."
                ),
                confirmLabel: _t("Yes"),
            });
            if (!(confirmed && (partner = await this.pos.selectPartner()))) {
                return false;
            }
        }
        return partner;
    },
    async settleOrderDues(partner, paylaterPaymentMethod, settleLines) {
        const order = this.order;
        const commercialPartnerId = order.commercialPartnerId;
        const amountToSettle = order.getSettleAmount();
        if (commercialPartnerId && commercialPartnerId == partner.raw.commercial_partner_id) {
            const confirmed = await ask(this.pos.dialog, {
                title: _t("Settle due orderlines"),
                body: _t(
                    "Do you want to deposit %s to %s?",
                    this.pos.env.utils.formatCurrency(amountToSettle),
                    partner.name
                ),
                confirmLabel: _t("Yes"),
            });
            if (confirmed) {
                const result = order.addPaymentline(paylaterPaymentMethod);
                if (!result.status) {
                    return false;
                }

                result.data.setAmount(-amountToSettle);
                settleLines.forEach((line) => (line.qty = 0));
                return super.validateOrder(...arguments);
            }
        } else {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t(
                    "The selected customer is not in the list of partners of the ongoing settling orderlines."
                ),
            });
        }
    },
    async depositOrder(partner, change, paylaterPaymentMethod) {
        const confirmed = await ask(this.pos.dialog, {
            title: _t("The order is empty"),
            body: _t(
                "Do you want to deposit %s to %s?",
                this.pos.env.utils.formatCurrency(change),
                partner.name
            ),
            confirmLabel: _t("Yes"),
        });
        if (confirmed) {
            await this.pos.addLineToCurrentOrder({
                price_unit: change,
                qty: 1,
                taxes_id: [],
                product_tmpl_id: this.pos.config.deposit_product_id,
            });
            const result = this.order.addPaymentline(paylaterPaymentMethod);
            if (!result.status) {
                return false;
            }

            result.data.setAmount(-change);
            const depositLines = this.order.lines.filter((l) => l.isDepositLine());
            depositLines.forEach((line) => (line.qty = 0));
            return super.validateOrder(...arguments);
        }
    },
});
