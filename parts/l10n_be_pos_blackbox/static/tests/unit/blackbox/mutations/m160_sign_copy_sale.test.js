import { test, expect, describe } from "@odoo/hoot";
import {
    generatePosOrder,
    setupPosBlackboxEnv,
    expectGeneralProperties,
    setOrderFdmSignature,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m160_sign_copy_sale.json' for an example request
describe("sign_copy_sale", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const partner = models["res.partner"].find((p) => p.name === "BE Company CoA");
        const order = generatePosOrder(
            models,
            [
                {
                    product_id: martini.id,
                    qty: 2,
                    price_unit: martini.lst_price,
                    tax_ids: martini.taxes_id.map((t) => t.id),
                },
            ],
            [
                {
                    amount: 52,
                    reference: "Test Payment",
                    uuid: "fake-uuid-1234",
                    payment_method_id: models["pos.payment.method"].find((m) => m.name === "Cash")
                        .id,
                },
            ]
        );
        setOrderFdmSignature(order);
        order.update({
            l10n_be_short_signature: "short-signature",
            partner_id: partner.id,
        });

        const response = await store.blackbox.signCopy.sign(order, "1234567890");
        const input = response.formatted;
        const fdmRef = input.fdmRef;
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });

        // Check previous fdm reference
        expect(fdmRef.eventCounter).toBe(1);
        expect(fdmRef.eventLabel).toBe("N");
        expect(fdmRef.fdmId).toBe("1234567890");
        expect(fdmRef.totalCounter).toBe(100);
    });

    test("called at right time", async () => {
        let blackboxIsCalled = false;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M160_signCopy") {
                blackboxIsCalled = true;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store, {}, true);
        setOrderFdmSignature(order);
        order.nb_print = 1;
        order.l10n_be_short_signature = "short-signature";
        await store.syncAllOrders();
        const comp = await mountWithCleanup(TicketScreen, {});
        await comp.print(order);
        expect(blackboxIsCalled).toBe(true);
    });
});
