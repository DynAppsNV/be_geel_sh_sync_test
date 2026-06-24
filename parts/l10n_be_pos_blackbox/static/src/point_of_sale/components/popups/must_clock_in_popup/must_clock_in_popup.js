import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

class CustomDialog extends Dialog {
    onEscape() {}
}

export class MustClockInPopup extends Component {
    static template = "l10n_be_pos_blackbox.MustClockInPopup";
    static components = { Dialog: CustomDialog };

    setup() {
        this.pos = usePos();
    }
    async clockIn() {
        await this.pos.handleClockInOut(this.pos.getCashier(), "in");
        this.props.close();
    }
}
