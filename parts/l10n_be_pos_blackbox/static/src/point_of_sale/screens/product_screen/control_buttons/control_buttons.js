import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { CustomSelectCreateDialog } from "@point_of_sale/app/components/custom_select_create_dialog/custom_select_create_dialog";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        this.report = useService("report");
    },
    async clickPrintBill() {
        if (!this.pos.blackbox.isActive || !this.pos.getOrder().getOrderlines().length) {
            return await super.clickPrintBill();
        }
        const order = this.pos.getOrder();
        try {
            const identifier = this.pos.getCashier().l10n_be_insz_or_bis_number;
            // We must await the signOrder must sent before 'signPreBill'
            await this.pos.blackbox.signOrder.sign(order, identifier);
            // We must await the signPreBill because we need blackbox response to display it on the receipt
            const result = await this.pos.blackbox.signPreBill.sign(
                order,
                identifier,
                this.pos.printer.hardware_proxy.printer?.url
            );
            if (!result) {
                return false;
            }
            await super.clickPrintBill();
        } finally {
            order.uiState["PRE_BILL"] = {};
        }
    },
    openSplitPage() {
        if (!this.pos.blackbox.isActive) {
            return super.openSplitPage(...arguments);
        }
        const identifier = this.pos.getCashier().l10n_be_insz_or_bis_number;
        // Before splitting an order, we push the potential changes to the order to the blackbox
        this.pos.blackbox.signOrder.sign(this.pos.getOrder(), identifier);
        return super.openSplitPage(...arguments);
    },

    onClickSalesReports() {
        this.pos.openSalesReportsList(this.report);
    },
    onClickUserReports() {
        const domain = [
            ["config_id", "=", this.pos.config.id],
            ["pos_clock_in_out_ids", "!=", false],
        ];
        this.dialog.add(CustomSelectCreateDialog, {
            resModel: "pos.session",
            listViewId: this.pos.models["ir.ui.view"].find(
                (v) => v.name == "pos_session_reports_list_view"
            )?.id,
            noCreate: true,
            multiSelect: false,
            domain,
            context: {},
            onSelected: async (resIds) => {
                const sessionId = resIds[0];
                const res = await this.report.doAction(
                    "l10n_be_pos_blackbox.action_report_pos_user",
                    [sessionId]
                );
                if (res?.success) {
                    const [session] = await this.pos.data.read(
                        "pos.session",
                        [sessionId],
                        ["state"]
                    );
                    this.pos.signUserReport(
                        sessionId,
                        session.state === "closed" ? "closed" : "opened"
                    );
                }
            },
        });
    },
});
