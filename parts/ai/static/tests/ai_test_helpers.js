import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { AIAgent } from "./mock_server/mock_models/ai_agent";
import { AIComposer } from "./mock_server/mock_models/ai_composer";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";

export function defineAIModels() {
    return defineModels(aiModels);
}

export const aiModels = { ...mailModels, DiscussChannel, AIAgent, AIComposer };
