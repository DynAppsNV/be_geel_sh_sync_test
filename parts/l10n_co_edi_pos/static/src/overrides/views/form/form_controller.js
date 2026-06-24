/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    // @Override
    async afterExecuteActionButton(clickParams) {
        const result = await super.afterExecuteActionButton(clickParams);
        if (clickParams.name === "button_l10n_co_dian_refresh_data") {
            const pos = this.env.services.pos;
            await pos.data.read("res.partner", [this.model.root.resId]);
        }
        return result;
    },
});
