import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    setupPosBlackboxEnv,
    expectGeneralProperties,
    getComboOrder,
    expectFinancial,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/uc200_composite_product.json' for an example request
describe("composite_product", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const menu = models["product.product"].find((m) => m.name === "Business Menu All-In");
        const starter = models["product.product"].find((m) => m.name === "Carpaccio Beef");
        const main = models["product.product"].find((m) => m.name === "Burger of the Chef");
        const wine = models["product.product"].find((m) => m.name === "Matching Wines");
        const order = getComboOrder(store, true);

        const response = await store.blackbox.signSale.sign(order, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const subProducts = transactions[0].subProducts;
        const financials = input.financials;

        // Check general properties
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });
        expect(transactions).toHaveLength(1);
        expect(input.transaction.transactionTotal).toBe(58);

        // Check combo main transaction line
        expectTransactionLine(transactions[0], menu, 1, "PIECE", 58, "A", "COMPOSITE_PRODUCT");

        // Check sub products
        expect(subProducts).toHaveLength(3);

        const first = subProducts[0];
        const firstPriceChange = starter.lst_price - order.lines[1].price_unit;
        expect(first.productId).toBe(`product_id_${starter.id}`);
        expect(first.productName).toBe(starter.name);
        expect(first.quantity).toBe(1);
        expect(first.quantityType).toBe("PIECE");
        expect(first.unitPrice).toBe(starter.lst_price);
        expect(first.vats).toHaveLength(1);
        expect(first.vats[0].label).toBe("B");
        expect(first.vats[0].price).toBe(starter.lst_price);
        expect(first.vats[0].priceChanges).toHaveLength(1);
        expect(first.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(first.vats[0].priceChanges[0].type).toBe("INTERNAL");
        expect(first.vats[0].priceChanges[0].name).toBe("MENU_DISCOUNT");
        expect(first.vats[0].priceChanges[0].amount).toBeCloseTo(-firstPriceChange);

        const second = subProducts[1];
        const secondPriceChange = main.lst_price - order.lines[2].price_unit;
        expect(second.productId).toBe(`product_id_${main.id}`);
        expect(second.productName).toBe(main.name);
        expect(second.quantity).toBe(1);
        expect(second.quantityType).toBe("PIECE");
        expect(second.unitPrice).toBe(main.lst_price);
        expect(second.vats).toHaveLength(1);
        expect(second.vats[0].label).toBe("B");
        expect(second.vats[0].price).toBe(main.lst_price);
        expect(second.vats[0].priceChanges).toHaveLength(1);
        expect(second.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(second.vats[0].priceChanges[0].type).toBe("INTERNAL");
        expect(second.vats[0].priceChanges[0].name).toBe("MENU_DISCOUNT");
        expect(second.vats[0].priceChanges[0].amount).toBeCloseTo(-secondPriceChange);

        const third = subProducts[2];
        const thirdPriceChange = wine.lst_price - order.lines[3].price_unit;
        expect(third.productId).toBe(`product_id_${wine.id}`);
        expect(third.productName).toBe(wine.name);
        expect(third.quantity).toBe(1);
        expect(third.quantityType).toBe("PIECE");
        expect(third.unitPrice).toBe(wine.lst_price);
        expect(third.vats).toHaveLength(1);
        expect(third.vats[0].label).toBe("A");
        expect(third.vats[0].price).toBe(wine.lst_price);
        expect(third.vats[0].priceChanges).toHaveLength(1);
        expect(third.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(third.vats[0].priceChanges[0].type).toBe("INTERNAL");
        expect(third.vats[0].priceChanges[0].name).toBe("MENU_DISCOUNT");
        expect(third.vats[0].priceChanges[0].amount).toBeCloseTo(-thirdPriceChange);
        const basePrice = wine.lst_price + main.lst_price + starter.lst_price;
        const totalPriceChange = firstPriceChange + secondPriceChange + thirdPriceChange;
        expect(basePrice - totalPriceChange).toBeCloseTo(menu.lst_price);
        // Check payment details
        expectFinancial(financials[0], "Cash", "PAYMENT", 58, "CASH");
    });
});
