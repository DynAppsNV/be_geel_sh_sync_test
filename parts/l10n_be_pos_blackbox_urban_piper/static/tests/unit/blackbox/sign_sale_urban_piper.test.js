import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    expectGeneralProperties,
    payOrder,
    expectFinancial,
    expectCostCenter,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { setupPosBlackboxUrbanPiperEnv } from "@l10n_be_pos_blackbox_urban_piper/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PosStore } from "@point_of_sale/app/services/pos_store";

definePosModels();

describe("sign_sale from urban piper", () => {
    patchWithCleanup(TicketScreen.prototype, {
        _fetchSyncedOrders() {
            return;
        },
    });
    patchWithCleanup(PosStore.prototype, {
        async getServerOrders() {
            return [];
        },
    });

    test("check signSale from urban piper called when `_doneOrder()`", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };
        const store = await setupPosBlackboxUrbanPiperEnv(expectRequest);
        const models = store.models;
        const partner = models["res.partner"].get(9);
        const bourgogne = models["product.product"].find((p) => p.name === "Bourgogne Red");
        const chardonnay = models["product.product"].find((p) => p.name === "Chardonnay White");

        const order = await getFilledOrder(store);
        order.setPartner(partner);
        order.delivery_provider_id = 1;
        order.delivery_json = "{}";
        payOrder(store, order);

        const comp = await mountWithCleanup(TicketScreen, {});
        await comp._doneOrder(order);
        expect(blackboxIsCalled).toBe(true);

        expectGeneralProperties(request, {
            order: order,
            employeeId: "97121722222",
            ticketMedium: "DIGITAL",
        });

        const transactions = request.transaction.transactionLines;
        const financials = request.financials;

        expectCostCenter(
            request.costCenter,
            partner.id.toString() + " " + partner.name,
            "PLATFORM",
            partner.vat
        );

        expect(transactions).toHaveLength(2);
        expectTransactionLine(transactions[0], bourgogne, 3, "PIECE", 35, "A", "SINGLE_PRODUCT");
        expectTransactionLine(transactions[1], chardonnay, 2, "PIECE", 40, "A", "SINGLE_PRODUCT");

        expect(financials).toHaveLength(1);
        expectFinancial(financials[0], "Cash", "PAYMENT", 185, "CASH");
    });

    test("check signSale from urban piper called when `_fetchUrbanpiperOrderCount()`", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };
        const store = await setupPosBlackboxUrbanPiperEnv(expectRequest);
        const models = store.models;
        const partner = models["res.partner"].get(9);
        const bourgogne = models["product.product"].find((p) => p.name === "Bourgogne Red");
        const chardonnay = models["product.product"].find((p) => p.name === "Chardonnay White");

        const order = await getFilledOrder(store);
        order.setPartner(partner);
        order.delivery_provider_id = 1;
        order.delivery_status = "food_ready";
        payOrder(store, order);

        await store._fetchUrbanpiperOrderCount(order.id);
        expect(blackboxIsCalled).toBe(true);

        expectGeneralProperties(request, {
            order: order,
            employeeId: "97121722222",
            ticketMedium: "DIGITAL",
        });

        const transactions = request.transaction.transactionLines;
        const financials = request.financials;

        expectCostCenter(
            request.costCenter,
            partner.id.toString() + " " + partner.name,
            "PLATFORM",
            partner.vat
        );

        expect(transactions).toHaveLength(2);
        expectTransactionLine(transactions[0], bourgogne, 3, "PIECE", 35, "A", "SINGLE_PRODUCT");
        expectTransactionLine(transactions[1], chardonnay, 2, "PIECE", 40, "A", "SINGLE_PRODUCT");

        expect(financials).toHaveLength(1);
        expectFinancial(financials[0], "Cash", "PAYMENT", 185, "CASH");
    });
});
