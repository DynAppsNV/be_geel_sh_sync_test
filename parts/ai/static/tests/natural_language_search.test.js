import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    defineActions,
    defineMenus,
    defineModels,
    fields,
    MockServer,
    models,
    mountWebClient,
    serverState,
} from "@web/../tests/web_test_helpers";

defineActions([
    {
        id: 667,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[false, "kanban"]],
    },
    {
        id: 668,
        xml_id: "action_2",
        name: "Partners Action 2",
        res_model: "partner",
        views: [[false, "list"]],
    },
]);
defineMenus([
    {
        id: 1,
        name: "App1",
        appID: 1,
        actionID: 667,
    },
    {
        id: 2,
        name: "App2",
        appID: 2,
        actionID: 668,
    },
]);
class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();

    _records = [{ id: 1, name: "dummy record", foo: "yop" }];
    _views = {
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `
            <list>
                <field name="foo"/>
            </list>
        `,
    };
}
defineModels([Partner]);
defineMailModels();

test.tags("desktop");
test("Opening a view with an agent updates the menu", async () => {
    await mountWebClient();
    expect(".o_menu_brand").toHaveText("App1");
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "AI_OPEN_MENU_LIST", { menuID: 2 });
    await waitFor(".o_list_view");
    expect(".o_menu_brand").toHaveText("App2");
});
