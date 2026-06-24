import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    initState() {
        super.initState();
        if (this.isCountryGermanyAndFiskaly() && this.config.module_pos_restaurant) {
            this.uiState = {
                ...this.uiState,
                tx_revision: this.uiState.tx_revision || 1,
                l10n_de_fiskaly_order_tx_uuid: this.uiState.l10n_de_fiskaly_order_tx_uuid || false,
            };
        }
    },
    export_for_printing(baseUrl, headerData) {
        const receipt = super.export_for_printing(...arguments);
        if (
            this.isCountryGermanyAndFiskaly() &&
            this.config.module_pos_restaurant &&
            this.isTransactionFinished()
        ) {
            receipt["tss"] = {
                ...receipt["tss"],
                erstBestellung: {
                    name: "TSE-Erstbestellung",
                    value: this.l10n_de_fiskaly_time_start,
                },
            };
        }
        return receipt;
    },
});
