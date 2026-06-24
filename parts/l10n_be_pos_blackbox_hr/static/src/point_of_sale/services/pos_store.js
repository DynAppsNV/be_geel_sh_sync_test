import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        if (this.blackbox.isActive) {
            this.data.connectWebSocket("CLOCKING", (payload) => {
                if (payload.session_id == this.session.id) {
                    this.models.connectNewData(payload.data);
                    if (!this.isCashierClockedIn()) {
                        this.showLoginScreen();
                    }
                }
            });
        }
    },
    canLoginCashier(cashier) {
        if (this.blackbox?.isActive && this.config.module_pos_hr) {
            if (!cashier.l10n_be_insz_or_bis_number) {
                this.dialog.add(AlertDialog, {
                    title: _t("INSZ or BIS number missing"),
                    body: _t(
                        "The National Register number is missing for this employee. Please update the employee information."
                    ),
                });
                return false;
            }
        }
        return super.canLoginCashier(cashier);
    },
    isCashierClockedIn(cashierId = this.getCashier().id) {
        return this.config.module_pos_hr
            ? this.session.l10n_be_employees_clocked_ids.map((e) => e.id).includes(cashierId)
            : super.isCashierClockedIn(...arguments);
    },
});
