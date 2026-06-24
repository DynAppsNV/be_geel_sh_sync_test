import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    //@Override
    setup() {
        super.setup(...arguments);
        if (this.pos.isCountryGermanyAndFiskaly()) {
            const _super_handlePushOrderError = this._handlePushOrderError.bind(this);
            this._handlePushOrderError = async (error) => {
                if (error.code === "fiskaly") {
                    this.pos.fiskalyError(error);
                } else {
                    _super_handlePushOrderError(error);
                }
            };
            this.pos.validateOrderFree = true;
        }
    },
});
