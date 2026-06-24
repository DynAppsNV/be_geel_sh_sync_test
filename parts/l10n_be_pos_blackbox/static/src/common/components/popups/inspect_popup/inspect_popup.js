import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class InspectPopup extends Component {
    static components = { Dialog };
    static template = "l10n_be_pos_blackbox.InspectPopup";
    static props = ["request", "response", "close"];

    setup() {
        this.dialog = useService("dialog");
    }

    get requestString() {
        return JSON.stringify(this.props.request, null, 4);
    }

    get responseString() {
        return JSON.stringify(this.props.response, null, 4);
    }

    async copyRequest() {
        await navigator.clipboard.writeText(this.requestString);
    }

    async copyResponse() {
        await navigator.clipboard.writeText(this.responseString);
    }
}
