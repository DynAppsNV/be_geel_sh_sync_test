import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/app/models/pos_config";
import { isFiscalPrinterActive } from "./helpers/utils";

patch(PosConfig.prototype, {
    get autoPrint() {
        return isFiscalPrinterActive(this) || super.autoPrint;
    },
});
