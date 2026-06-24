import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { ConnectionLostError } from "@web/core/network/rpc";
import { L10nBeBlackboxError } from "@l10n_be_pos_blackbox/common/blackbox/utils/blackbox_error";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(OrderPaymentValidation.prototype, {
    async validateOrder() {
        if (!this.pos.blackbox.isActive) {
            return super.validateOrder(...arguments);
        }

        // Stop the process if the blackbox is not reachable, the user
        // shouldn't be able to print ticket or validate orders without
        // blackbox signature.
        const pingResult = await this.pos.blackbox.ping();
        if (pingResult) {
            return super.validateOrder(...arguments);
        }

        this.pos.dialog.add(AlertDialog, {
            title: _t("Network Error"),
            body: _t(
                "With a blackbox, a network error will prevent the order from being signed. Please check your connection and try again."
            ),
        });
        return false;
    },
    async afterOrderValidation() {
        if (this.order.state == "paid" && !this.order.l10n_be_short_signature) {
            try {
                await this.pos.preSyncAllOrders([this.order]);
            } catch (error) {
                if (error instanceof ConnectionLostError) {
                    this.order.state = "draft";
                    throw error;
                }
            }
        }
        return super.afterOrderValidation();
    },

    get canPrintReceipt() {
        const res = super.canPrintReceipt;
        return this.pos.blackbox.isActive
            ? res && Boolean(this.order.l10n_be_short_signature)
            : res;
    },

    handleValidationError(error) {
        if (!this.pos.blackbox.isActive) {
            return super.handleValidationError(error);
        }
        try {
            // If it's a blackbox error, no need to retry since it has already been handled
            // If it's a blackbox reachable error, we will not be able to reach blackbox either
            if (
                error instanceof L10nBeBlackboxError ||
                error.message.includes("Failed to fetch") ||
                error.message.includes("HTTP Error")
            ) {
                this.order.state = "draft";
                return error;
            }
            // Otherwise, we will try to sign the order again
            return super.handleValidationError(error);
        } catch (e) {
            if (
                e instanceof L10nBeBlackboxError ||
                error.message.includes("Failed to fetch") ||
                error.message.includes("HTTP Error")
            ) {
                this.order.state = "draft";
            }
            throw error;
        }
    },
    async finalizeValidation() {
        if (!this.pos.blackbox.isActive) {
            return super.finalizeValidation(...arguments);
        }
        await this.pos.finalizeOrderCorrection(this.order);
        return super.finalizeValidation(...arguments);
    },
});
