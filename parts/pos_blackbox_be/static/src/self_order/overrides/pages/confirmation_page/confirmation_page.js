import { patch } from "@web/core/utils/patch";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { rpc } from "@web/core/network/rpc";

patch(ConfirmationPage.prototype, {
    async beforePrintOrder() {
        // We only sign Kiosk order here, cause Mobile clients can never land on this page (causing order never send to blackbox)
        // So we now sign mobile orders inside "_send_self_order_receipt" backend method
        if (this.selfOrder.config.iface_fiscal_data_module) {
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                rpc(`/pos_blackbox_be/send_order/`, {
                    access_token: this.selfOrder.access_token,
                    order_access_token: this.props.orderAccessToken,
                    order_id: this.confirmedOrder.id,
                });
                return false;
            }
            if (this.selfOrder.config.self_ordering_mode === "mobile") {
                for (let i = 0; i < 5; i++) {
                    const data = await rpc(`/pos_blackbox_be/get_signed_order/`, {
                        access_token: this.selfOrder.access_token,
                        order_access_token: this.props.orderAccessToken,
                        order_id: this.confirmedOrder.id,
                    });
                    if (data) {
                        Object.assign(this.confirmedOrder, data);
                        this.confirmedOrder.uiState.receipt_type = "NS";
                        return true;
                    }
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                }
                return false;
            }
        }
        return super.beforePrintOrder();
    },

    get printOptions() {
        if (this.selfOrder.config.iface_fiscal_data_module) {
            return Object.assign(super.printOptions, { blackboxPrint: true });
        }
        return super.printOptions;
    },

    canPrintReceipt() {
        const result = super.canPrintReceipt();
        if (this.selfOrder.config.iface_fiscal_data_module) {
            return result && Boolean(this.confirmedOrder.blackbox_signature);
        }
        return result;
    },
});
