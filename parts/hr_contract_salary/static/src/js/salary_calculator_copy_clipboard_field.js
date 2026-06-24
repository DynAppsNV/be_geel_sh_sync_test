import { CopyButton } from "@web/core/copy_button/copy_button";
import { CopyClipboardButtonField, copyClipboardButtonField } from "@web/views/fields/copy_clipboard/copy_clipboard_field";
import { registry } from "@web/core/registry";

export class SaveAndCopyButton extends CopyButton {
    static props = {
        ...CopyButton.props,
        record: {type: Object},
    }
    async onClick() {
        await this.props.record.model.root.save();
        return super.onClick();
    }
}

export class SaveAndCopyToClipboardButtonField extends CopyClipboardButtonField{
    static template = "web.SaveAndCopyToClipboardButtonField";
    static components = { SaveAndCopyButton };
};

const saveAndCopyToClipboardButtonField = {
    ...copyClipboardButtonField,
    component: SaveAndCopyToClipboardButtonField,
};

registry.category("fields").add("SaveAndCopyToClipboardButton", saveAndCopyToClipboardButtonField);
