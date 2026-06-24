import {
    click,
    contains,
    insertText,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";

import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { defineAIModels } from "../ai_test_helpers";

describe.current.tags("desktop");
defineAIModels();

test("posting in ai chat triggers agent response generation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Agent Partner" });
    const aiAgentId = pyEnv["ai.agent"].create({
        name: "Agent Partner",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "ai_chat",
        ai_agent_id: aiAgentId,
    });
    onRpc("/ai/generate_response", () => {
        expect.step("generate_response");
        return true;
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow .o-mail-Composer-input");
    await insertText(".o-mail-ChatWindow .o-mail-Composer-input", "AI is bad at writing code");
    await press("Enter");
    await expect.waitForSteps(["generate_response"]);
});
