import { UserCommandPlugin } from "@html_editor/core/user_command_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { patch } from "@web/core/utils/patch";

patch(UserCommandPlugin.prototype, {
    getCommand(commandId) {
        const command = super.getCommand(commandId);
        return {
            ...command,
            isAvailable: (selection) => {
                if (closestElement(selection.anchorNode, ".o_editor_prompt")) {
                    // Only the "openDynamicPlaceholder" and history commands are
                    // available inside a prompt.
                    return ["openDynamicPlaceholder", "historyUndo", "historyRedo"].includes(
                        commandId
                    );
                }
                return !command.isAvailable || command.isAvailable(selection);
            },
        };
    },
});
