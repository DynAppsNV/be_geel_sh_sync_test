import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup();
        this.printer = useService("printer");
        this.ui = useService("ui");
    },
    async closeSession() {
        if (!this.pos.blackbox.isActive) {
            return super.closeSession();
        }
        try {
            const isSessionClosable = await this.pos.data.call(
                "pos.session",
                "is_session_closable",
                [this.pos.session.id, this.bankPaymentMethodDiffPairs]
            );
            if (isSessionClosable) {
                const usr = this.pos.getCashier().l10n_be_insz_or_bis_number;
                await this.pos.workOutAllCashiers();
                await this.generateZReports(this.pos.session.id, usr);
                this.pos.resetCashier();
            }
        } catch (error) {
            console.warn("Error during Z reports generation:", error);
        }
        return await super.closeSession();
    },
    async generateZReports(sessionId, usr) {
        try {
            this.ui.block();
            const [saleDetails, userReportData] = await Promise.all([
                this.pos.data.call(
                    "report.point_of_sale.report_saledetails",
                    "get_sale_details",
                    [false, false, false, [sessionId]],
                    { before_closing: true }
                ),
                this.pos.data.call("pos.session", "get_l10n_be_user_report_data", [
                    sessionId,
                    true,
                ]),
            ]);
            this.pos.blackbox.signReportTurnoverZ.signWithDelay(
                this.pos.models,
                saleDetails,
                sessionId,
                usr
            );

            this.pos.blackbox.signReportUserZ.signWithDelay(
                this.pos.models,
                userReportData,
                sessionId,
                usr
            );
            await this.pos.data.call("pos.session", "generate_l10n_z_reports_attachments", [
                sessionId,
                saleDetails,
                userReportData,
            ]);
        } finally {
            this.ui.unblock();
        }
    },
    async downloadSalesReport() {
        if (this.pos.blackbox.isActive) {
            return this.pos.openSalesReportsList(this.report, this.pos.session.id);
        } else {
            return super.downloadSalesReport();
        }
    },
    async openDetailsPopup() {
        if (this.pos.blackbox.isActive) {
            await this.pos.blackbox.signDrawerOpen.sign(
                this.pos.models,
                this.pos.getCashier().l10n_be_insz_or_bis_number
            );
        }
        return super.openDetailsPopup();
    },
});
