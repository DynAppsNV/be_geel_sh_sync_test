import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class PlatformOrderProvider extends models.ServerModel {
    _name = "platform.order.provider";

    _load_pos_data_fields() {
        return ["name", "code"];
    }

    _records = [{ id: 1, name: "FoodPanda", code: "foodpanda" }];
}

patch(hootPosModels, [...hootPosModels, PlatformOrderProvider]);
