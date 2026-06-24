import { test } from "@odoo/hoot";
import { makeMockServer, onRpc, getService } from "@web/../tests/web_test_helpers";
import {
    triggerHotkey,
    start,
    insertText,
    contains,
    click,
} from "@mail/../tests/mail_test_helpers";
import { defineAIModels } from "@ai/../tests/ai_test_helpers";

defineAIModels();

test("[text composer] can open chat with @agent in command palette with focused composer", async () => {
    const mockServer = await makeMockServer();

    const partnerId = mockServer.env["res.partner"].create({
        name: "Test agent",
        active: false,
    });
    mockServer.env["ai.agent"].create({
        name: "Test agent",
        partner_id: partnerId,
    });

    onRpc("ai.agent", "get_ask_ai_agent", () => ({ id: 1, name: "ASK AI" }));

    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await contains(".o_command_category>.text-uppercase", { text: "Agents" });
    await insertText("input[placeholder='Search a conversation']", "Test agent");
    await click(".o_command.focused:has(.fa-gear)", { text: "Test agent" });
    await contains(".o-mail-ChatWindow", { text: "Test agent" });
    await contains(".o-mail-Composer.o-focused");
});

test.tags("html composer");
test("can open chat with @agent in command palette with focused composer", async () => {
    const mockServer = await makeMockServer();
    const partnerId = mockServer.env["res.partner"].create({
        name: "AI Agent",
    });
    mockServer.env["ai.agent"].create({
        name: "Test Agent",
        partner_id: partnerId,
    });
    onRpc("get_ask_ai_agent", () => ({ id: 1, name: "ASK AI" }));
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await insertText("input[placeholder='Search a conversation']", "AI Agent");
    await click(".o_command.focused:has(.fa-gear)", { text: "AI Agent" });
    await contains(".o-mail-ChatWindow", { text: "AI Agent" });
    await contains(".o-mail-Composer.o-focused");
});
