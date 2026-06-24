import { setupPosBlackboxEnv } from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { registry } from "@web/core/registry";
import { unpatchPrepDataService } from "@pos_enterprise/app/services/data_service";
import { unpatchDataServiceOptions } from "@pos_enterprise/app/models/data_service_options";

export const setupPosBlackboxUrbanPiperEnv = async (...args) => {
    unpatchPrepDataService();
    unpatchDataServiceOptions();
    registry.category("services").remove("preparation_display");
    return setupPosBlackboxEnv(...args);
};
