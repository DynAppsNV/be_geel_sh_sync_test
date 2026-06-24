import { patch } from "@web/core/utils/patch";
import { iotDeviceFormView } from "@iot/backend/iot_device_form";

patch(iotDeviceFormView.Controller.prototype, {
    async onClickButtonTest(params) {
        if (params.clickParams.name === "test_device") {
            odoo.use_lna = (await this.orm.call("pos.printer", "use_local_network_access")).use_lna;
            this.env.services.iot_longpolling.setLna(odoo.use_lna);
        }
        return super.onClickButtonTest(params);
    },
});
