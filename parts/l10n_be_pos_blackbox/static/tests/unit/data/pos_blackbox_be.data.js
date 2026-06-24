import { patch } from "@web/core/utils/patch";
import { models } from "@web/../tests/web_test_helpers";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

export class PosBlackboxBe extends models.ServerModel {
    _name = "pos.blackbox.be";

    _load_pos_data_fields() {
        return [];
    }

    _records = [
        {
            id: 1,
            display_name: "Blackbox - 123456789",
            name: "Blackbox - 123456789",
            fdm_id: "123456789",
            pos_config_ids: [1],
            local_ip: "0.0.0.0",
            use_lna: false,
        },
    ];
}

patch(hootPosModels, [...hootPosModels, PosBlackboxBe]);
