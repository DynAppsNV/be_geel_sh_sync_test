import { patch } from "@web/core/utils/patch";
import { ExportAuditReportToPDFDialog } from "@accountant_knowledge/components/export_audit_report_to_pdf_dialog/export_audit_report_to_pdf_dialog";

patch(ExportAuditReportToPDFDialog.prototype, {
    async exportAuditReportToPDF() {
        if (this.props.record.data.inherited_esg_report_id?.records.length) {
            this.props.close();
            await this.action.doAction({
                type: "ir.actions.act_url",
                target: "download",
                url: `/esg_csrd/article/${this.props.record.resId}/esg_report?include_pdf_files=${this.state.includePdfFiles}&include_child_articles=${this.state.includeChildArticles}`,
            });
        } else {
            await super.exportAuditReportToPDF();
        }
    },
});
