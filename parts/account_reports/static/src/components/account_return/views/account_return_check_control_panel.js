import { ControlPanel } from "@web/search/control_panel/control_panel";

export class AccountReturnCheckControlPanel extends ControlPanel {
    static template = "account_reports.account_return_check_control_panel";

    _isEmbeddedActionVisible(_action) {
        return true;
    }

    setup() {
        super.setup();
        this.state.embeddedInfos.showEmbedded = true;
    }
}
