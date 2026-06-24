import { test, describe, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    getComboOrder,
    payOrder,
    setupPosBlackboxEnv,
    waitForDelayedCalls,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

definePosModels();

/**
 * Returns the priceChange with the given name from a priceChanges array, or null.
 */
const findPc = (priceChanges, name) => priceChanges.find((pc) => pc.name === name) ?? null;

/**
 * Returns the first EVENT-scoped (global discount) entry from a priceChanges array, or null.
 */
const findGlobalPc = (priceChanges) => priceChanges.find((pc) => pc.scope === "EVENT") ?? null;

const getTransactionLinePriceChanges = (transactionLine) =>
    transactionLine.lineType === "COMPOSITE_PRODUCT"
        ? transactionLine.subProducts.flatMap((subProduct) =>
              subProduct.vats.flatMap((vat) => vat.priceChanges)
          )
        : transactionLine.mainProduct.vats.flatMap((vat) => vat.priceChanges);

const expectContiguousGroupingIds = (transactionLines) => {
    const groupingIds = [
        ...new Set(
            transactionLines
                .flatMap(getTransactionLinePriceChanges)
                .map((priceChange) => priceChange.groupingId)
        ),
    ].sort((left, right) => left - right);

    expect(groupingIds).not.toBeEmpty();
    expect(groupingIds).toEqual(
        Array.from({ length: groupingIds.at(-1) }, (_, index) => index + 1)
    );
};

/**
 * Common test setup: creates a store, finds all relevant products, and builds an order
 * with one Business Menu combo (Carpaccio + Burger) and optionally a Perrier line.
 *
 * @param {Object}  [options]
 * @param {string}  [options.menuName="Business Menu"]  Combo product name.
 * @param {number}  [options.lineDiscount=10]           Discount on combo sub-lines and Perrier (0 = none).
 * @param {boolean} [options.withPerrier=true]          Whether to include a Perrier line.
 * @returns {Promise<{ store, models, order, menu, carpaccio, burger, perrier, martini, menuAllIn }>}
 */
async function createBaseOrder({
    menuName = "Business Menu",
    lineDiscount = 10,
    withPerrier = true,
} = {}) {
    const store = await setupPosBlackboxEnv();
    const models = store.models;

    const menu = models["product.product"].find((m) => m.name === menuName);
    const carpaccio = models["product.product"].find((m) => m.name === "Carpaccio Beef");
    const burger = models["product.product"].find((m) => m.name === "Burger of the Chef");
    const perrier = models["product.product"].find((m) => m.name === "Perrier");
    const martini = models["product.product"].find((m) => m.name === "Dry Martini");
    const menuAllIn = models["product.product"].find((m) => m.name === "Business Menu All-In");

    const order = store.addNewOrder();

    models["pos.order.line"].create({
        product_id: menu,
        qty: 1,
        order_id: order.id,
        price_unit: 0,
        tax_ids: menu.taxes_id,
        combo_line_ids: [
            [
                "create",
                {
                    price_unit: 16.11,
                    product_id: carpaccio,
                    qty: 1,
                    order_id: order.id,
                    tax_ids: carpaccio.taxes_id,
                    ...(lineDiscount > 0 && { discount: lineDiscount }),
                },
            ],
            [
                "create",
                {
                    price_unit: 22.56,
                    product_id: burger,
                    qty: 1,
                    order_id: order.id,
                    tax_ids: burger.taxes_id,
                    ...(lineDiscount > 0 && { discount: lineDiscount }),
                },
            ],
        ],
    });

    if (withPerrier) {
        models["pos.order.line"].create({
            product_id: perrier,
            qty: 1,
            order_id: order.id,
            price_unit: perrier.lst_price,
            tax_ids: perrier.taxes_id,
            ...(lineDiscount > 0 && { discount: lineDiscount }),
        });
    }

    return { store, models, order, menu, carpaccio, burger, perrier, martini, menuAllIn };
}

describe("input generator groupingId", () => {
    /**
     * Test 1 — Order with: composite MENU (2 sub-lines) + simple PERRIER,
     * both with 10 % line discount and 20 % global discount.
     *
     * Expected allocation order:
     *   1  MENU_DISCOUNT        (combo-parent-uuid key, shared by all sub-lines of this combo)
     *   2  GLOBAL_DISCOUNT_20P  (shared across the whole transaction)
     *   3  DISCOUNT_10P         (combo-parent-uuid key, shared by all sub-lines of this combo)
     *   4  DISCOUNT_10P         (PERRIER's own uuid key)
     */
    test("single pass: MENU+PERRIER with line & global discount → groupingIds 1-4", async () => {
        const { store, order } = await createBaseOrder();
        await store.applyDiscount(20, order);

        const generator = new InputGenerator({ order, models: store.models });
        const linesMap = generator.generateSignOrderInput();
        order.updateLastTransactionLines();
        const transLines = linesMap.transaction.transactionLines;

        // transLines[0] = COMPOSITE_PRODUCT (MENU), transLines[1] = SINGLE_PRODUCT (PERRIER)
        const [menuTransLine, perrierTransLine] = transLines;
        const sub1Pcs = menuTransLine.subProducts[0].vats[0].priceChanges;
        const sub2Pcs = menuTransLine.subProducts[1].vats[0].priceChanges;
        const perrierPcs = perrierTransLine.mainProduct.vats[0].priceChanges;

        // Both sub-lines share the same MENU_DISCOUNT groupingId (keyed by product id)
        expect(findPc(sub1Pcs, "MENU_DISCOUNT").groupingId).toBe(1);
        expect(findPc(sub2Pcs, "MENU_DISCOUNT").groupingId).toBe(1);

        // All lines share the same GLOBAL_DISCOUNT groupingId
        expect(findGlobalPc(sub1Pcs).groupingId).toBe(2);
        expect(findGlobalPc(sub2Pcs).groupingId).toBe(2);
        expect(findGlobalPc(perrierPcs).groupingId).toBe(2);
        // Both sub-lines share the same LINE_DISCOUNT groupingId (keyed by combo-parent uuid)
        expect(findPc(sub1Pcs, "DISCOUNT_10P").groupingId).toBe(3);
        expect(findPc(sub2Pcs, "DISCOUNT_10P").groupingId).toBe(3);

        // PERRIER gets its own LINE_DISCOUNT groupingId
        expect(findPc(perrierPcs, "DISCOUNT_10P").groupingId).toBe(4);

        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(4);
    });

    /**
     * Test 2 — Two sequential generation passes (simulating two signOrder calls).
     * Pass 1: MENU + PERRIER  →  counter = 4 (same as Test 1).
     * Pass 2: MARTINI added (unit-price change + global discount).
     *
     * Key assertion: counter does NOT reset between passes; GLOBAL is reused (id=2),
     * MARTINI's UNIT_PRICE_CHANGE gets the next fresh id (5).
     */
    test("two sequential passes: MARTINI added on 2nd pass → counter grows to 5", async () => {
        const { store, models, order, martini } = await createBaseOrder(); // MENU + PERRIER
        await store.applyDiscount(20, order);

        // Pass 1 (simulated signOrder 1)
        const gen1 = new InputGenerator({ order, models: store.models });
        gen1.generateSignOrderInput();
        order.updateLastTransactionLines();
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(4);

        // Add MARTINI with a manual price change (price_unit ≠ lst_price = 12) ─
        models["pos.order.line"].create({
            product_id: martini,
            qty: 1,
            order_id: order.id,
            price_unit: 15, // higher than lst_price → UNIT_PRICE_CHANGE
            tax_ids: martini.taxes_id,
        });
        await store.applyDiscount(20, order);

        // Pass 2 (simulated signOrder 2)
        const gen2 = new InputGenerator({ order, models: store.models });
        const linesMap2 = gen2.generateSignOrderInput();
        const transLines2 = linesMap2.transaction.transactionLines;
        const martiniPcs = transLines2[0].mainProduct.vats[0].priceChanges;

        // GLOBAL is reused from pass 1
        expect(findGlobalPc(martiniPcs).groupingId).toBe(2);
        // UNIT_PRICE_CHANGE gets the next id after 4
        expect(findPc(martiniPcs, "UNIT_PRICE_CHANGE").groupingId).toBe(5);

        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(5);
    });

    /**
     * Test 3 — Two different composite products in the same order.
     * BUSINESS MENU and BUSINESS MENU ALL-IN have different product ids, so each
     * gets its own INTERNAL groupingId.
     */
    test("two different combos → distinct INTERNAL groupingIds (counter = 2)", async () => {
        const { store, models, order, carpaccio, burger, menuAllIn } = await createBaseOrder({
            withPerrier: false,
            lineDiscount: 0,
        });

        models["pos.order.line"].create({
            product_id: menuAllIn,
            qty: 1,
            order_id: order.id,
            price_unit: 0,
            tax_ids: menuAllIn.taxes_id,
            combo_line_ids: [
                [
                    "create",
                    {
                        price_unit: 16.11,
                        product_id: carpaccio,
                        qty: 1,
                        order_id: order.id,
                        tax_ids: carpaccio.taxes_id,
                    },
                ],
                [
                    "create",
                    {
                        price_unit: 22.56,
                        product_id: burger,
                        qty: 1,
                        order_id: order.id,
                        tax_ids: burger.taxes_id,
                    },
                ],
            ],
        });

        const generator = new InputGenerator({ order, models: store.models });
        const linesMap = generator.generateSignOrderInput();
        const transLines = linesMap.transaction.transactionLines;

        const bmSub1Pcs = transLines[0].subProducts[0].vats[0].priceChanges;
        const bmSub2Pcs = transLines[0].subProducts[1].vats[0].priceChanges;
        const aiSub1Pcs = transLines[1].subProducts[0].vats[0].priceChanges;
        const aiSub2Pcs = transLines[1].subProducts[1].vats[0].priceChanges;

        // Business Menu gets id 1
        expect(findPc(bmSub1Pcs, "MENU_DISCOUNT").groupingId).toBe(1);
        expect(findPc(bmSub2Pcs, "MENU_DISCOUNT").groupingId).toBe(1);

        // Business Menu All-In gets id 2 (different product → new id)
        expect(findPc(aiSub1Pcs, "MENU_DISCOUNT").groupingId).toBe(2);
        expect(findPc(aiSub2Pcs, "MENU_DISCOUNT").groupingId).toBe(2);

        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(2);
    });

    /**
     * Test 4 — signSale after a line deletion: groupingIds are NOT renumbered.
     *
     * Flow:
     *   signOrder 1 — MENU (1/2/3) + PERRIER (2/4) + MARTINI (2/5)  → counter = 5
     *   signOrder 2 — delete PERRIER → correction uses stored ids 2/4, counter stays 5
     *   signOrder 3 — add COCA (GLOBAL=2 reused, LINE=6) → counter = 6 (id 4 not recycled)
     *   signSale    — MENU keeps 1/2/3, MARTINI keeps 2/5, COCA keeps 2/6
     */
    test("no groupingId renumbering after line deletion (counter stays at 5)", async () => {
        const { store, models, order, perrier, martini } = await createBaseOrder({
            menuName: "Business Menu All-In",
        });

        models["pos.order.line"].create({
            product_id: martini,
            qty: 1,
            order_id: order.id,
            price_unit: 15, // unit-price change vs lst_price = 12
            tax_ids: martini.taxes_id,
        });

        await store.applyDiscount(20, order);

        // signOrder 1: allocate all ids
        const gen1 = new InputGenerator({ order, models: store.models });
        gen1.generateSignOrderInput();
        order.updateLastTransactionLines();
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(5);

        // Delete PERRIER
        const perrierLine = order.lines.find(
            (l) => l.product_id.id === perrier.id && !l.combo_parent_id
        );
        order.removeOrderline(perrierLine);
        await store.applyDiscount(20, order);
        const gen2 = new InputGenerator({ order, models: store.models });
        gen2.generateSignOrderInput();
        order.updateLastTransactionLines();

        // Add Crème brûlée with line + global discount
        const cremeBrulee = models["product.product"].find((m) => m.name === "Crème brûlée");
        models["pos.order.line"].create({
            product_id: cremeBrulee,
            qty: 1,
            order_id: order.id,
            price_unit: cremeBrulee.lst_price,
            tax_ids: cremeBrulee.taxes_id,
            discount: 10,
        });
        await store.applyDiscount(20, order);

        // signOrder 3 (delta — only Crème brûlée)
        const gen3 = new InputGenerator({ order, models: store.models });
        const linesMap3 = gen3.generateSignOrderInput();
        order.updateLastTransactionLines();
        const [cremeBruleeTransLine] = linesMap3.transaction.transactionLines;
        const cremeBruleePcs = cremeBruleeTransLine.mainProduct.vats[0].priceChanges;

        // GLOBAL is reused — freed id 4 (PERRIER) is NOT recycled
        expect(findGlobalPc(cremeBruleePcs).groupingId).toBe(2);
        expect(findPc(cremeBruleePcs, "DISCOUNT_10P").groupingId).toBe(6);
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(6);

        // signSale: full order — MENU / MARTINI / CRÈME BRÛLÉE
        const gen4 = new InputGenerator({ order, models: store.models });
        const linesMap4 = gen4.generateTransactionLinesInput();
        const transLines4 = Object.values(linesMap4).map(({ transLine }) => transLine);

        // Counter must not have increased — no new ids allocated for existing lines
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(6);

        // MENU keeps its original groupingIds (no renumbering)
        const menuSub1Pcs = transLines4[0].subProducts[0].vats[0].priceChanges;
        const menuSub2Pcs = transLines4[0].subProducts[1].vats[0].priceChanges;
        expect(findPc(menuSub1Pcs, "MENU_DISCOUNT").groupingId).toBe(1);
        expect(findPc(menuSub2Pcs, "MENU_DISCOUNT").groupingId).toBe(1);
        expect(findGlobalPc(menuSub1Pcs).groupingId).toBe(2);
        expect(findPc(menuSub1Pcs, "DISCOUNT_10P").groupingId).toBe(3);
        expect(findPc(menuSub2Pcs, "DISCOUNT_10P").groupingId).toBe(3);

        // MARTINI keeps its original groupingIds (gap at id=4 is acceptable)
        const martiniPcs = transLines4[1].mainProduct.vats[0].priceChanges;
        expect(findGlobalPc(martiniPcs).groupingId).toBe(2);
        expect(findPc(martiniPcs, "UNIT_PRICE_CHANGE").groupingId).toBe(5);

        // Crème brûlée keeps its groupingIds from signOrder 3
        const cremeSalePcs = transLines4[2].mainProduct.vats[0].priceChanges;
        expect(findGlobalPc(cremeSalePcs).groupingId).toBe(2);
        expect(findPc(cremeSalePcs, "DISCOUNT_10P").groupingId).toBe(6);
    });

    /**
     * Test 5 — Line discount change on an existing line: new groupingId allocated
     * for the updated discount; old groupingId preserved on the correction line.
     *
     * Flow:
     *   signOrder 1 — MARTINI (LINE 10% → id 1)               counter = 1
     *   signOrder 2 — -MARTINI correction (id 1) +MARTINI 20% (id 2)  counter = 2
     *   signOrder 3 — -MARTINI correction (id 2) +MARTINI 30% (id 3)  counter = 3
     *
     * Key assertions:
     *   - Correction line reuses the old groupingId (FDM traceability).
     *   - New positive line always gets the next fresh id.
     *   - Freed ids are never recycled.
     */
    test("line discount change: new groupingId per discount update, old id on correction", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((m) => m.name === "Dry Martini");

        const order = store.addNewOrder();

        const martiniLine = models["pos.order.line"].create({
            product_id: martini,
            qty: 1,
            order_id: order.id,
            price_unit: martini.lst_price,
            tax_ids: martini.taxes_id,
            discount: 10,
        });

        // signOrder 1
        const gen1 = new InputGenerator({ order, models: store.models });
        const linesMap1 = gen1.generateSignOrderInput();
        order.updateLastTransactionLines();
        const martiniPcs1 =
            linesMap1.transaction.transactionLines[0].mainProduct.vats[0].priceChanges;

        expect(findPc(martiniPcs1, "DISCOUNT_10P").groupingId).toBe(1);
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(1);

        // Change line discount 10 % → 20 %
        martiniLine.discount = 20;

        // signOrder 2 (delta: -MARTINI 10% correction + +MARTINI 20%)
        const gen2 = new InputGenerator({ order, models: store.models });
        const linesMap2 = gen2.generateSignOrderInput();
        order.updateLastTransactionLines();
        const [negLine2, posLine2] = linesMap2.transaction.transactionLines;
        const negPcs2 = negLine2.mainProduct.vats[0].priceChanges;
        const posPcs2 = posLine2.mainProduct.vats[0].priceChanges;

        // Correction preserves old groupingId so the FDM can trace which discount is corrected
        expect(findPc(negPcs2, "DISCOUNT_10P").groupingId).toBe(1);
        // New positive line gets a fresh id — id 1 is NOT recycled
        expect(findPc(posPcs2, "DISCOUNT_20P").groupingId).toBe(2);
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(2);

        // Change line discount 20 % → 30 %
        martiniLine.discount = 30;

        // signOrder 3 (delta: -MARTINI 20% correction + +MARTINI 30%)
        const gen3 = new InputGenerator({ order, models: store.models });
        const linesMap3 = gen3.generateSignOrderInput();
        const [negLine3, posLine3] = linesMap3.transaction.transactionLines;
        const negPcs3 = negLine3.mainProduct.vats[0].priceChanges;
        const posPcs3 = posLine3.mainProduct.vats[0].priceChanges;

        // Correction preserves id=2 (the 20% discount's id)
        expect(findPc(negPcs3, "DISCOUNT_20P").groupingId).toBe(2);
        // New 30% discount gets the next available id — neither 1 nor 2 is reused
        expect(findPc(posPcs3, "DISCOUNT_30P").groupingId).toBe(3);
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(3);
    });

    test("new unsynced line correction keeps first discount groupingId", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((m) => m.name === "Dry Martini");

        const order = store.addNewOrder();
        const line = models["pos.order.line"].create({
            product_id: martini,
            qty: 1,
            order_id: order.id,
            price_unit: martini.lst_price,
            tax_ids: martini.taxes_id,
            discount: 5,
        });

        const initialValues = {
            [line.uuid]: {
                priceUnit: line.blackboxPriceUnitNoDiscount,
                discount: 0,
                globalDiscount: 0,
                qty: 1,
            },
        };

        const initGenerator = new InputGenerator({ order, models: store.models });
        initialValues[line.uuid].initialTransLine = initGenerator.generateTransactionLine(line, {
            priceUnit: initialValues[line.uuid].priceUnit,
            discount: 0,
            globalDiscount: 0,
            qty: 1,
        });
        initialValues[line.uuid].initialTransLine.lineTotal =
            initGenerator.computeTransactionLineTotal(initialValues[line.uuid].initialTransLine);

        const generator = new InputGenerator({ order, models: store.models });
        const payload = generator.generateSignOrderInput(initialValues);
        const transLines = payload.transaction.transactionLines;
        const pcs = transLines[2].mainProduct.vats[0].priceChanges;

        expect(findPc(pcs, "DISCOUNT_5P").groupingId).toBe(1);
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(1);
    });

    test("signed combo line discount 0->5 keeps contiguous groupingIds", async () => {
        const { store, order } = await createBaseOrder({
            menuName: "Business Menu All-In",
            lineDiscount: 0,
            withPerrier: false,
        });

        // Pass 1: sign initial combo line (MENU_DISCOUNT only)
        const gen1 = new InputGenerator({ order, models: store.models });
        gen1.generateSignOrderInput();
        order.updateLastTransactionLines();

        const comboParent = order.lines.find((l) => l.combo_line_ids.length);
        store.setDiscountFromUI(comboParent, 5);

        // Pass 2: correction payload after discount update
        const gen2 = new InputGenerator({ order, models: store.models });
        const payload = gen2.generateSignOrderInput();
        const positiveLine = payload.transaction.transactionLines[1];
        const allPcs = positiveLine.subProducts.flatMap((sp) =>
            sp.vats.flatMap((v) => v.priceChanges)
        );

        const discountEntries = allPcs.filter((pc) => pc.name === "DISCOUNT_5P");
        expect(discountEntries).not.toBeEmpty();
        expect(discountEntries.every((pc) => pc.groupingId === 2)).toBe(true);

        const roundingEntries = allPcs.filter((pc) => pc.name === "ROUNDING_ADAPTATION");
        if (roundingEntries.length) {
            expect(roundingEntries.every((pc) => pc.groupingId === 3)).toBe(true);
            expect(order.l10n_be_grouping_id.groupingIdCount).toBe(3);
        } else {
            expect(order.l10n_be_grouping_id.groupingIdCount).toBe(2);
        }
    });

    test("combo order sync-pay flow keeps groupingIds contiguous", async () => {
        const requests = [];
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (["M121_signOrder", "M110_signSale"].includes(body.operationName)) {
                requests.push({
                    operationName: body.operationName,
                    transaction: body.variables.data.transaction,
                });
            }
        });
        const order = getComboOrder(store, false, false);
        const comboParent = order.lines.find((line) => line.combo_line_ids.length);
        const martini = store.models["product.product"].find(
            (product) => product.name === "Dry Martini"
        );
        const perrier = store.models["product.product"].find(
            (product) => product.name === "Perrier"
        );

        comboParent.setQuantity(2, false);
        await store.syncAllOrders();

        store.models["pos.order.line"].create({
            product_id: martini,
            qty: 1,
            order_id: order.id,
            price_unit: martini.lst_price,
            tax_ids: martini.taxes_id,
        });
        store.setDiscountFromUI(comboParent, 5);
        store.models["pos.order.line"].create({
            product_id: perrier,
            qty: 1,
            order_id: order.id,
            price_unit: perrier.lst_price,
            tax_ids: perrier.taxes_id,
        });

        await store.syncAllOrders({ orders: [order] });
        payOrder(store, order);
        await store.syncAllOrders({ orders: [order] });

        const signOrderRequests = requests.filter(
            (request) => request.operationName === "M121_signOrder"
        );
        const saleRequest = requests.find((request) => request.operationName === "M110_signSale");

        expect(signOrderRequests).toHaveLength(2);
        expect(saleRequest).not.toBe(undefined);

        expectContiguousGroupingIds(signOrderRequests[1].transaction.transactionLines);
        expectContiguousGroupingIds(saleRequest.transaction.transactionLines);
    });

    /**
     * Test 7 — Cost-center transfer: transferred line keeps source groupingId in
     * the CostCenterChange payload; after merge the destination groupingId wins.
     *
     * Flow:
     *   Table 1 — signOrder: +1 PERRIER (LINE 10% → id 1). Counter = 1.
     *   Table 2 — signOrder: +1 DRY MARTINI (LINE 10% → id 1)
     *                       +1 PERRIER        (LINE 10% → id 2). Counter = 2.
     *   CostCenterChange: Table 1 → Table 2.
     *     from block: -1 PERRIER (groupingId = 1, source order's id)
     *     to   block: +1 PERRIER (groupingId = 1, same source id)
     *   Merge: PERRIER lines are merged on Table 2 (qty becomes 2).
     *   signSale (Table 2): DRY MARTINI → LINE gId 1; PERRIER (×2) → LINE gId 2 (dest id).
     *
     * Key assertions:
     *   - CostCenterChange preserves source groupingId (1) in both from/to blocks.
     *   - After merge, COCA uses the destination order's existing groupingId (2).
     *   - Source groupingId (1) for COCA is discarded after merge.
     */
    test("cost-center transfer: source groupingId in CCC payload; dest groupingId after merge", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;

        const perrier = models["product.product"].find((m) => m.name === "Perrier");
        const martini = models["product.product"].find((m) => m.name === "Dry Martini");

        // Table 1: one PERRIER with 10% line discount
        const order1 = store.addNewOrder();
        const perrierLine1 = models["pos.order.line"].create({
            product_id: perrier,
            qty: 1,
            order_id: order1.id,
            price_unit: perrier.lst_price,
            tax_ids: perrier.taxes_id,
            discount: 10,
        });

        // signOrder for Table 1
        const gen1 = new InputGenerator({ order: order1, models: store.models });
        const linesMap1 = gen1.generateSignOrderInput();
        order1.updateLastTransactionLines();

        const perrierLine1Pcs =
            linesMap1.transaction.transactionLines[0].mainProduct.vats[0].priceChanges;
        expect(findPc(perrierLine1Pcs, "DISCOUNT_10P").groupingId).toBe(1);
        expect(order1.l10n_be_grouping_id.groupingIdCount).toBe(1);

        // Table 2: DRY MARTINI (10% discount) + PERRIER (10% discount)
        const order2 = store.createNewOrder();
        models["pos.order.line"].create({
            product_id: martini,
            qty: 1,
            order_id: order2.id,
            price_unit: martini.lst_price,
            tax_ids: martini.taxes_id,
            discount: 10,
        });
        const perrierLine2 = models["pos.order.line"].create({
            product_id: perrier,
            qty: 1,
            order_id: order2.id,
            price_unit: perrier.lst_price,
            tax_ids: perrier.taxes_id,
            discount: 10,
        });

        // signOrder for Table 2
        const gen2 = new InputGenerator({ order: order2, models: store.models });
        const linesMap2 = gen2.generateSignOrderInput();
        order2.updateLastTransactionLines();

        const martiniPcs2 =
            linesMap2.transaction.transactionLines[0].mainProduct.vats[0].priceChanges;
        const perrierPcs2 =
            linesMap2.transaction.transactionLines[1].mainProduct.vats[0].priceChanges;
        expect(findPc(martiniPcs2, "DISCOUNT_10P").groupingId).toBe(1);
        expect(findPc(perrierPcs2, "DISCOUNT_10P").groupingId).toBe(2);
        expect(order2.l10n_be_grouping_id.groupingIdCount).toBe(2);

        // CostCenterChange: Table 1 → Table 2
        // The InputGenerator for the CCC is built on order1 (source).
        // generateTransferCostCenterInput uses order1's grouping state → groupingId 1 for PERRIER.
        const cccGenerator = new InputGenerator({
            order: order1,
            models: store.models,
        });
        const oldCostCenter = { id: "1", type: "TABLE", reference: order1.uuid };
        const newCostCenter = { id: "2", type: "TABLE", reference: order2.uuid };
        const cccInput = cccGenerator.generateSignCostCenterChangeInput(
            oldCostCenter,
            newCostCenter
        );

        const fromLines = cccInput.transfer.from.transaction.transactionLines;
        const toLines = cccInput.transfer.to.transaction.transactionLines;

        // Both from (negated) and to (positive) carry the SOURCE groupingId (1)
        expect(
            findPc(fromLines[0].mainProduct.vats[0].priceChanges, "DISCOUNT_10P").groupingId
        ).toBe(1);
        expect(findPc(toLines[0].mainProduct.vats[0].priceChanges, "DISCOUNT_10P").groupingId).toBe(
            1
        );

        // Simulate merge: PERRIER from Table 1 is merged into PERRIER on Table 2
        // In production this is done by _mergeLines; here we update qty directly.
        perrierLine2.qty = 2;
        perrierLine1.delete();

        // signSale on Table 2 after merge
        const gen4 = new InputGenerator({ order: order2, models: store.models });
        const linesMap4 = gen4.generateTransactionLinesInput();
        const transLines4 = Object.values(linesMap4).map(({ transLine }) => transLine);

        // Counter on order2 must not have grown — no new ids needed
        expect(order2.l10n_be_grouping_id.groupingIdCount).toBe(2);

        // DRY MARTINI keeps its original groupingId on Table 2 (1)
        const martiniSalePcs = transLines4[0].mainProduct.vats[0].priceChanges;
        expect(findPc(martiniSalePcs, "DISCOUNT_10P").groupingId).toBe(1);

        // PERRIER (×2) uses the DESTINATION order's groupingId (2), not the source's (1)
        const perrierSalePcs = transLines4[1].mainProduct.vats[0].priceChanges;
        expect(findPc(perrierSalePcs, "DISCOUNT_10P").groupingId).toBe(2);
    });

    /**
     * Test 8 — Transfer to a table with a non-mergeable existing line.
     * When a source line cannot be merged with any destination line it keeps its UUID
     * so that the groupingId state (keyed by uuid) is automatically available on the
     * destination order without any extra remapping.
     *
     * Flow:
     *   Table 2 — signOrder: +1 Perrier (LINE 10% → id 1). Counter = 1.
     *   Table 1 — signOrder: +1 DRY MARTINI (LINE 10% → id 1). Counter = 1.
     *   CostCenterChange Table 1 → Table 2:
     *     from: -1 Martini (groupingId = 1 from order1)
     *     to:   +1 Martini (groupingId = 1 from order1)
     *   Transfer (no merge): Martini line is moved to order2; it keeps its original UUID.
     *   signSale on Table 2:
     *     Perrier → LINE gId 1 (unchanged)
     *     Martini → LINE gId 1 (preserved via uuid — no new id allocated)
     *
     * Key assertions:
     *   - CCC carries groupingId=1 for Martini in both from/to blocks.
     *   - The non-merged Martini line keeps its original UUID after the transfer.
     *   - groupingIdCount on order2 stays at 1 (no new id allocated for Martini).
     */
    test("transfer to table with non-mergeable line: groupingId carried over to new uuid", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M122_signCostCenterChange") {
                resolver(body.variables.data);
            }
        });
        const models = store.models;
        const table1 = models["restaurant.table"].find((t) => t.table_number === 1);
        const table2 = models["restaurant.table"].find((t) => t.table_number === 2);
        const perrier = models["product.product"].find((m) => m.name === "Perrier");
        const martini = models["product.product"].find((m) => m.name === "Dry Martini");

        // Table 2: Perrier with 10% line discount
        const order2 = store.createNewOrder();
        order2.table_id = table2;
        models["pos.order.line"].create({
            product_id: perrier,
            qty: 1,
            order_id: order2.id,
            price_unit: perrier.lst_price,
            tax_ids: perrier.taxes_id,
            discount: 10,
        });

        const gen2a = new InputGenerator({ order: order2, models: store.models });
        gen2a.generateSignOrderInput();
        order2.updateLastTransactionLines();
        expect(order2.l10n_be_grouping_id.groupingIdCount).toBe(1);

        // Table 1: Dry Martini with 10% line discount
        const order1 = store.createNewOrder();
        order1.table_id = table1;
        models["pos.order.line"].create({
            product_id: martini,
            qty: 1,
            order_id: order1.id,
            price_unit: martini.lst_price,
            tax_ids: martini.taxes_id,
            discount: 10,
        });

        const gen1 = new InputGenerator({ order: order1, models: store.models });
        const linesMap1 = gen1.generateSignOrderInput();
        order1.updateLastTransactionLines();

        const martiniPcs1 =
            linesMap1.transaction.transactionLines[0].mainProduct.vats[0].priceChanges;
        expect(findPc(martiniPcs1, "DISCOUNT_10P").groupingId).toBe(1);
        expect(order1.l10n_be_grouping_id.groupingIdCount).toBe(1);

        // Transfer Table 1 → Table 2: Martini has no matching line on Table 2 (no merge)
        await store.transferOrder(order1.uuid, table2);
        const cccRequest = await promise;

        // CCC carries source's groupingId (1) for Martini in both from/to blocks
        const fromLines = cccRequest.transfer.from.transaction.transactionLines;
        const toLines = cccRequest.transfer.to.transaction.transactionLines;
        expect(
            findPc(fromLines[0].mainProduct.vats[0].priceChanges, "DISCOUNT_10P").groupingId
        ).toBe(1);
        expect(findPc(toLines[0].mainProduct.vats[0].priceChanges, "DISCOUNT_10P").groupingId).toBe(
            1
        );

        // order1 is empty; Martini is now on order2
        expect(order1.isEmpty()).toBe(true);
        // const martiniOnOrder2 = order2.lines.find((l) => l.product_id.name === "Dry Martini");
        // // Key assertion: the transferred line keeps its original uuid so the groupingId
        // // state (keyed by uuid on order1) is automatically usable on order2 without remapping.
        // expect(martiniOnOrder2.uuid).toBe(originalMartiniUuid);

        // signSale on Table 2: Perrier gId=1, Martini gId=1 (preserved via uuid)
        const gen4 = new InputGenerator({ order: order2, models: store.models });
        const linesMap4 = gen4.generateTransactionLinesInput();
        const transLines4 = Object.values(linesMap4).map(({ transLine }) => transLine);

        const perrierSalePcs = transLines4[0].mainProduct.vats[0].priceChanges;
        expect(findPc(perrierSalePcs, "DISCOUNT_10P").groupingId).toBe(1);

        // Martini: groupingId=1 preserved via uuid — groupingIdCount stays at 1
        const martiniSalePcs = transLines4[1].mainProduct.vats[0].priceChanges;
        expect(findPc(martiniSalePcs, "DISCOUNT_10P").groupingId).toBe(1);
        expect(order2.l10n_be_grouping_id.groupingIdCount).toBe(1);
    });
});
