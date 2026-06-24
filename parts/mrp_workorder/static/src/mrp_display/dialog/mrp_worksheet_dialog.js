import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import DocumentViewer from "@mrp_workorder/components/viewer";
import { HtmlField } from "@html_editor/fields/html_field";

export class MrpWorksheetDialog extends ConfirmationDialog {
    static props = {
        ...ConfirmationDialog.props,
        body: { optional: true },
        worksheetData: [Object, Boolean],
        record: Object,
    };
    static template = "mrp_workorder.MrpWorksheetDialog";
    static components = {
        ...ConfirmationDialog.components,
        DocumentViewer,
        HtmlField,
    };

    get htmlInfo() {
        return {
            name: "note",
            record: this.props.record,
            readonly: true,
            embeddedComponents: true,
        }
    }
}
