import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    _getRewardLineValuesProduct(args) {
        const res = super._getRewardLineValuesProduct(...arguments);
        if (this.config_id.l10n_be_blackbox_be_id) {
            const rewardedProduct = this._getRewardedProduct(args["reward"], args);
            // Save the rewarded product on the line to be able to retrieve the transaction line for which we must apply the price change
            res[0].rewarded_product_id = rewardedProduct;
        }
        return res;
    },
    get linesSendableToBlackbox() {
        const lines = super.linesSendableToBlackbox;
        // We exclude reward lines as we don't want to send them to the blackbox
        return lines.filter((line) => !line.is_reward_line);
    },
});
