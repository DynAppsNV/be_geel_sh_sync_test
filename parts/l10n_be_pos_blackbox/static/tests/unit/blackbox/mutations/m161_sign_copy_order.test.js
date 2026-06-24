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

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m161_sign_copy_order.json' for an example request
describe("sign_copy_order", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const partner = models["res.partner"].find((p) => p.name === "BE Company CoA");
        const order = generatePosOrder(models, [
            {
                product_id: martini.id,
                qty: 2,
                price_unit: martini.lst_price,
                tax_ids: martini.taxes_id,
            },
        ]);
        order.update({
            l10n_be_fdm_date_time: "2023-10-01 12:00:00",
            l10n_be_event_label: "P",
            l10n_be_event_counter: 1,
            l10n_be_total_counter: 100,
            l10n_be_fdm_id: "1234567890",
            l10n_be_short_signature: "short-signature",
            partner_id: partner.id,
        });

        const response = await store.blackbox.signCopy.sign(order, "1234567890");
        const input = response.formatted;
        const fdmRef = input.fdmRef;
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });

        // Check previous fdm reference
        expect(fdmRef.eventCounter).toBe(1);
        expect(fdmRef.eventLabel).toBe("P");
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
        const order = await getFilledOrder(store);
        order.nb_print = 1;
        order.state = "paid";
        setOrderFdmSignature(order);
        order.l10n_be_short_signature = "short-signature";
        await store.syncAllOrders();
        const comp = await mountWithCleanup(TicketScreen, {});
        await comp.print(order);
        expect(blackboxIsCalled).toBe(true);
    });
});
