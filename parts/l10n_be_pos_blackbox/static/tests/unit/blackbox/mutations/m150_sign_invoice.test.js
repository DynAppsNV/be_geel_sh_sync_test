import { test, expect, describe } from "@odoo/hoot";
import {
    generatePosOrder,
    setupPosBlackboxEnv,
    waitForDelayedCalls,
    expectGeneralProperties,
    setOrderFdmSignature,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m150_sign_invoice.json' for an example request
describe("sign_invoice", () => {
    test("data generation", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M150_signInvoice") {
                resolver(body.variables.data);
            }
        });
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const burger = models["product.product"].find((p) => p.name === "Burger of the Chef");
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
                {
                    product_id: burger.id,
                    qty: 1,
                    price_unit: burger.lst_price,
                    tax_ids: burger.taxes_id.map((t) => t.id),
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

        await store.blackbox.signInvoice.sign(order, "1234567890");
        const input = await promise;
        const costCenter = input.costCenter;
        const fdmRef = input.fdmRefs[0];

        // Check general properties
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });
        expect(input.transaction).toBeEmpty();

        // Check if the cost center is customer
        expect(costCenter.type).toBe("CUSTOMER");
        expect(costCenter.id).toBe(partner.id.toString() + " " + partner.name);
        expect(costCenter.reference).toBe(partner.vat);

        // Check previous fdm reference
        expect(fdmRef.eventCounter).toBe(1);
        expect(fdmRef.eventLabel).toBe("N");
        expect(fdmRef.fdmId).toBe("1234567890");
        expect(fdmRef.totalCounter).toBe(100);
    });

    test("called at right time", async () => {
        let blackboxIsCalled = false;
        let order;

        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M150_signInvoice") {
                blackboxIsCalled = true;
            }
            if (body.operationName === "M110_signSale") {
                order.l10n_be_short_signature = "short-signature";
                setOrderFdmSignature(order);
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        order = await getFilledOrder(store, {}, true);
        const partner = store.models["res.partner"].getFirst();

        order.partner_id = partner;
        order.to_invoice = true;

        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);
    });
});
