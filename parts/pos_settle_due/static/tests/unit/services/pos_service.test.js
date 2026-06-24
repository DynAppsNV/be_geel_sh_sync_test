import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos_store.js", () => {
    test("getPartnerCredit", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(5);

        const partner = store.models["res.partner"].get(5);
        order.setPartner(partner);

        await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
        let partnerCreditInfo = store.getPartnerCredit(partner);

        expect(partnerCreditInfo).toMatchObject({
            creditLimit: 10,
            totalWithCart: 3.45,
            overDue: false,
            useLimit: false,
        });

        await store.addLineToOrder({ product_tmpl_id: product, qty: 2 }, order);
        partnerCreditInfo = store.getPartnerCredit(partner);

        expect(partnerCreditInfo).toMatchObject({
            creditLimit: 10,
            totalWithCart: 10.35,
            overDue: true,
            useLimit: true,
        });
    });
});
