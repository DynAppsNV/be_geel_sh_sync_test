import { CashierName } from "@point_of_sale/app/components/navbar/cashier_name/cashier_name";
import { patch } from "@web/core/utils/patch";

patch(CashierName.prototype, {
    get clockIconClass() {
        const clocked = this.pos.isCashierClockedIn();
        return {
            ...this.cssClass,
            "clock-status": true,
            "rounded-circle": true,
            "position-absolute": true,
            border: true,
            "border-light": true,
            "bg-success": clocked,
            "bg-danger": !clocked,
        };
    },
});
