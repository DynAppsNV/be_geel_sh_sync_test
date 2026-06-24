import { patch } from "@web/core/utils/patch";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { serializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";

patch(ConfirmationPage.prototype, {
    async beforePrintOrder() {
        const selfOrderConfig = this.selfOrder.config;
        if (
            selfOrderConfig.l10n_be_blackbox_be_id &&
            selfOrderConfig.self_ordering_mode === "kiosk"
        ) {
            try {
                const order = this.confirmedOrder;
                const usr = this.selfOrder.session.config_id._self_ordering_default_user_insz;
                const printerUrl = this.selfOrder.printer.device?.url;
                if (order.state == "paid") {
                    await this.selfOrder.blackbox.signSale.sign(order, usr, printerUrl);
                    await rpc(`/l10n_be_pos_blackbox_self_order/save_order_signature/`, {
                        access_token: this.selfOrder.access_token,
                        order_id: order.id,
                        order_access_token: order.access_token,
                        signature_data: {
                            l10n_be_short_signature: order.l10n_be_short_signature,
                            l10n_be_event_label: order.l10n_be_event_label,
                            l10n_be_event_counter: order.l10n_be_event_counter,
                            l10n_be_total_counter: order.l10n_be_total_counter,
                            l10n_be_fdm_id: order.l10n_be_fdm_id,
                            l10n_be_fdm_date_time: serializeDateTime(order.l10n_be_fdm_date_time),
                            l10n_be_pos_id: order.l10n_be_pos_id,
                            l10n_be_terminal_id: order.l10n_be_terminal_id,
                            l10n_be_device_id: order.l10n_be_device_id,
                            l10n_be_verification_url: order.l10n_be_verification_url,
                            l10n_be_pos_date_time: serializeDateTime(order.l10n_be_pos_date_time),
                            l10n_be_vat_calc: order.l10n_be_vat_calc,
                        },
                    });
                } else {
                    await this.selfOrder.blackbox.signPreBill.sign(order, usr, printerUrl);
                }
            } catch (error) {
                console.error("Error during blackbox signing:", error);
                return false;
            }
            return true;
        }
        return super.beforePrintOrder();
    },

    canPrintReceipt() {
        const result = super.canPrintReceipt();
        if (this.selfOrder.config.l10n_be_blackbox_be_id) {
            const order = this.confirmedOrder;
            return (
                result &&
                ((order.state == "paid" && Boolean(order.l10n_be_short_signature)) ||
                    (order.state != "paid" && order.l10n_be_event_label == "P"))
            );
        }
        return result;
    },
});
