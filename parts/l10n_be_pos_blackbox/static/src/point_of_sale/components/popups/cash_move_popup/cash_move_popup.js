import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { patch } from "@web/core/utils/patch";

patch(CashMovePopup.prototype, {
    setup() {
        super.setup();
        this.env.dialogData.dismiss = this.cancel.bind(this);
    },
    async confirm() {
        if (!this.pos.blackbox.isActive) {
            return super.confirm(...arguments);
        }

        const cashier = this.pos.getCashier().l10n_be_insz_or_bis_number;
        const amount = Math.abs(this.state.amount);
        let name = this.state.type;
        if (this.state.amount < 0) {
            name = name == "out" ? "in" : "out";
        }
        const result = await this.pos.blackbox.signMoneyInOut.sign(
            this.pos.models,
            cashier,
            {
                amount,
                name,
            },
            this.hardwareProxy.printer?.url
        );

        if (!result) {
            return false;
        }

        return super.confirm(...arguments);
    },
    async cancel() {
        if (!this.pos.blackbox.isActive) {
            return super.cancel(...arguments);
        }

        const cashier = this.pos.getCashier().l10n_be_insz_or_bis_number;
        const result = await this.pos.blackbox.signDrawerOpen.sign(this.pos.models, cashier);

        if (!result) {
            return false;
        }

        return super.cancel(...arguments);
    },
});
