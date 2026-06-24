import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async print(order) {
        if (this.pos.blackbox.isActive && order.finalized) {
            const usr = this.pos.getCashier().l10n_be_insz_or_bis_number;
            const printerUrl = this.pos.printer.hardware_proxy.printer?.url;
            // If the order was already printed
            if (order.nb_print > 0 && order.l10n_be_short_signature) {
                try {
                    const result = await this.pos.blackbox.signCopy.sign(order, usr, printerUrl);

                    if (!result) {
                        return false;
                    }
                    await super.print(order);
                } finally {
                    order.uiState["COPY"] = {};
                }
                return;
            } else if (order.nb_print === 0 && !order.l10n_be_short_signature) {
                await this.pos.blackbox.signSale.sign(order, usr, printerUrl);
            }
        }
        await super.print(order);
    },
});
