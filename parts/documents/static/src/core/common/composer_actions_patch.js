import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";
import {
    getAddDocumentDialogProps,
    SelectAddDocumentCreateDialog,
} from "@documents/views/view_dialogs/select_add_document_create_dialog";

registerComposerAction("add-documents", {
    icon: { template: "documents.DocumentsIcon" },
    name: _t("Add from Documents"),
    onSelected: ({ composer, store }) => {
        const thread = composer?.message?.thread || composer.targetThread;
        store.env.services.dialog.add(SelectAddDocumentCreateDialog, {
            ...getAddDocumentDialogProps(),
            chatterParams: {
                thread,
                composer,
            },
        });
    },
    sequence: 10,
});
