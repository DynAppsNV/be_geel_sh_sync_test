import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { BlackboxError } from "@pos_blackbox_be/pos/app/utils/blackbox_error";
import { ConnectionLostError } from "@web/core/network/rpc";
import { EMPTY_SIGNATURE } from "@pos_blackbox_be/pos/app/services/pos_store";

patch(OrderPaymentValidation.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.useBlackBoxBe() && !this.pos.userSessionStatus) {
            await this.pos.clock(true);
        }
        return super.validateOrder(isForceValidate);
    },
    async afterOrderValidation() {
        if (!this.order.blackbox_signature || this.order.blackbox_signature == EMPTY_SIGNATURE) {
            try {
                await this.pos.syncAllOrders({ orders: [this.order], throw: true });
            } catch (error) {
                if (error instanceof BlackboxError || error instanceof ConnectionLostError) {
                    this.order.state = "draft";
                    throw error;
                }
            }
        }
        return super.afterOrderValidation();
    },
    handleValidationError(error) {
        if (error instanceof BlackboxError) {
            this.order.state = "draft";
            error.retry ??= this.validateOrder.bind(this);
        }
        return super.handleValidationError(error);
    },
});
