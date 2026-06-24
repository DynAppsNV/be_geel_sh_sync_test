import { patch } from "@web/core/utils/patch";
import { models } from "@web/../tests/web_test_helpers";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

export class PosBlackboxLogDevice extends models.ServerModel {
    _name = "pos.blackbox.log.device";

    _load_pos_data_fields() {
        return [];
    }

    _records = [];

    log_device(self, config_id, device) {
        return true;
    }
}

patch(hootPosModels, [...hootPosModels, PosBlackboxLogDevice]);
