import { patch } from "@web/core/utils/patch";
import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";
import { BlackboxError } from "@pos_blackbox_be/pos/app/utils/blackbox_error";
import { onMounted } from "@odoo/owl";

patch(FeedbackScreen.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            // ensure amount_total is set to display the correct amount in the feedback screen
            // during FDM requests processing
            this.currentOrder.amount_total = this.currentOrder.priceIncl;
        });
    },
    async waiter() {
        this.state.fdmError = false;
        try {
            if (this.props.waitFor) {
                await this.props.waitFor;
            }
        } catch (e) {
            if (e instanceof BlackboxError) {
                this.state.fdmError = true;
                throw e;
            }
        } finally {
            this.state.loading = false;
            this.timeout = setTimeout(() => {
                this.goNext();
            }, 5000);
        }
    },

    goNext() {
        if (this.state.fdmError) {
            // do not finalize validation if there was an FDM error, and navigate back to payment screen
            this.currentOrder.amount_total = undefined; // reset amount_total on fdm error
            this.pos.navigate("PaymentScreen", { orderUuid: this.props.orderUuid });
        } else {
            super.goNext();
        }
    },
});
