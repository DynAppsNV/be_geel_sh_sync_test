import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class L10nBeBlackboxErrorPopup extends Component {
    static components = { Dialog };
    static template = "l10n_be_pos_blackbox.L10nBeBlackboxErrorPopup";
    static props = ["errors", "data", "close", "mutationName"];

    setup() {
        this.pos = usePos();
    }

    get order() {
        return this.props.data.order;
    }

    retry() {
        this.props.close();
        this.pos.syncAllOrders({ orders: [this.order] });
    }

    get showViewOrderButton() {
        const order = this.order;
        return order && order.state !== "paid";
    }

    viewOrder(order) {
        this.props.close();
        this.pos.setOrder(order);
        this.pos.navigate("ProductScreen", { orderUuid: this.pos.selectedOrderUuid });
    }
}
