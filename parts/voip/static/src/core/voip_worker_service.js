import { registry } from "@web/core/registry";

export class VoipWorkerClient {
    constructor(userAgent, workerService) {
        this.userAgent = userAgent;
        this.workerService = workerService;
    }

    handleMessage(message) {
        const { type, data } = message.data;
        if (!type?.startsWith("VOIP:")) {
            return;
        }
        switch (type) {
            case "VOIP:PLAY_INCOMING":
                this._onPlayIncoming(data.controlHandle);
                break;
            default:
                console.warn(`VoIP Worker Service received unknown message type: “${type}”`);
        }
    }

    send(action, data) {
        this.workerService.send(action, data);
    }

    _onPlayIncoming(controlHandle) {
        const session = this.userAgent.activeSession;
        if (!session || session.controlHandle !== controlHandle) {
            return;
        }
        session.ringleader = true;
        this.userAgent.requestIncomingRingtone();
    }
}

export const voipWorkerService = {
    dependencies: ["voip.user_agent", "worker_service"],
    start(_env, { "voip.user_agent": userAgent, worker_service: workerService }) {
        const client = new VoipWorkerClient(userAgent, workerService);
        workerService.registerHandler(client.handleMessage.bind(client));
        return client;
    },
};

registry.category("services").add("voip.worker", voipWorkerService);
