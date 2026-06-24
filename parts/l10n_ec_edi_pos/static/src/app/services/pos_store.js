import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData();
        if (this.isEcuadorianCompany()) {
            this["l10n_latam.identification.type"] =
                this.models["l10n_latam.identification.type"].getFirst();
        }
    },
    isEcuadorianCompany() {
        return this.company.country_id?.code == "EC";
    },
    getDefaultPartnerId() {
        if (this.isEcuadorianCompany()) {
            return this.config._final_consumer_id;
        }
        return super.getDefaultPartnerId();
    },
    // @Override
    // For EC, if the partner on the refund was End Consumer we need to allow the user to change it.
    // we also ensure, a customer is always selected
    async selectPartner() {
        if (!this.isEcuadorianCompany()) {
            return super.selectPartner(...arguments);
        }
        const currentOrder = this.getOrder();
        if (!currentOrder) {
            return;
        }
        const currentPartner = currentOrder.getPartner();
        if (
            currentOrder.getHasRefundLines() &&
            currentPartner?.id !== this.config._final_consumer_id
        ) {
            return super.selectPartner(...arguments);
        }

        this.dialog.add(PartnerList, {
            partner: currentPartner,
            getPayload: (newPartner) => {
                if (!newPartner) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Warning"),
                        body: _t("A customer is required. Select another to replace this one."),
                    });
                    return;
                }
                currentOrder.setPartner(newPartner);
            },
        });

        return currentPartner;
    },
});

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (this.company.country_id?.code == "EC") {
            this.to_invoice = true;
        }
    },
});
