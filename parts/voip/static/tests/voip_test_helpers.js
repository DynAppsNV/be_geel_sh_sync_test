import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mockWorker } from "@odoo/hoot-mock";
import { VoipWorker } from "@voip/worker/voip_worker";
import { defineModels, MockServer, mockService, onRpc } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import { MailActivity } from "./mock_server/mock_models/mail_activity";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { VoipCall } from "./mock_server/mock_models/voip_call";
import { VoipProvider } from "./mock_server/mock_models/voip_provider";

export function setupVoipTests() {
    onRpc("/voip/get_country_store", () => ({
        "res.country": {
            id: 1,
            name: "Belgium",
            code: "BE",
            phone_code: "32",
            image_url: "/base/static/img/flags/be.png",
        },
    }));
    const ringtones = {
        dial: {},
        incoming: {},
        ringback: {},
    };
    Object.values(ringtones).forEach((r) => Object.assign(r, { play: () => {} }));
    mockService("voip.ringtone", {
        ...ringtones,
        stopPlaying() {},
    });
    defineModels(voipModels);
    patch(MockServer.prototype, {
        start() {
            setupVoipWorker();
            return super.start(...arguments);
        },
    });
}

export const voipModels = {
    ...mailModels,
    MailActivity,
    ResPartner,
    ResUsers,
    VoipCall,
    VoipProvider,
};

let voipWorker = null;

/** @param {SharedWorker|Worker} worker */
function onWorkerConnected(worker) {
    const client = worker._messageChannel.port2;
    client.addEventListener("message", (ev) => {
        voipWorker.handleMessage(ev);
    });
    client.start();
}

function setupVoipWorker() {
    voipWorker = new VoipWorker();
    mockWorker(onWorkerConnected);
}
