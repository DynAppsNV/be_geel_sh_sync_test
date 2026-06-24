import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";

import { Registerer } from "@voip/core/registerer";
import { UserAgent } from "@voip/core/user_agent_service";

import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

function makeVoip() {
    return {
        env: {
            services: {
                "voip.user_agent": {
                    attemptReconnection() {},
                },
            },
        },
        isUnloading: false,
        resolveError() {},
        triggerError() {},
    };
}

test("register recreates SIP.js registerer stuck waiting", async () => {
    const sipRegisterers = [];
    const addEventListener = window.addEventListener.bind(window);

    class FakeEventEmitter {
        constructor(ownerIndex) {
            this.listeners = new Set();
            this.ownerIndex = ownerIndex;
        }

        addListener(listener) {
            this.listeners.add(listener);
        }

        removeListener(listener) {
            expect.step(`remove listener ${this.ownerIndex}`);
            this.listeners.delete(listener);
        }
    }

    patchWithCleanup(window, {
        addEventListener(type, listener, options) {
            if (type === "beforeunload") {
                return;
            }
            return addEventListener(type, listener, options);
        },
        SIP: {
            Registerer: class {
                constructor(userAgent, options) {
                    this.index = sipRegisterers.length;
                    this.options = options;
                    this.stateChange = new FakeEventEmitter(this.index);
                    this.waiting = this.index === 0;
                    sipRegisterers.push(this);
                }

                dispose() {
                    expect.step(`dispose ${this.index}`);
                    this.disposed = true;
                    return Promise.resolve();
                }

                register() {
                    expect.step(`register ${this.index}`);
                    return Promise.resolve(`registered ${this.index}`);
                }

                unregister() {}
            },
        },
    });

    const registerer = new Registerer(makeVoip(), {});
    const registerPromise = registerer.register();

    expect(typeof registerPromise.then).toBe("function");
    expect(sipRegisterers.length).toBe(2);
    expect(sipRegisterers[0].disposed).toBe(true);
    expect(sipRegisterers[0].stateChange.listeners.size).toBe(0);
    expect(sipRegisterers[1].options.expires).toBe(Registerer.EXPIRATION_INTERVAL);
    expect(await registerPromise).toBe("registered 1");
    expect.verifySteps(["remove listener 0", "dispose 0", "register 1"]);
});

test("attemptReconnection schedules a retry when registration rejects", async () => {
    const userAgent = Object.assign(Object.create(UserAgent.prototype), {
        __sipJsUserAgent: {
            reconnect() {
                expect.step("reconnect");
                return Promise.resolve();
            },
        },
        attemptingToReconnect: false,
        registerer: {
            register() {
                expect.step("register");
                return Promise.reject(new Error("REGISTER request already pending"));
            },
        },
        voip: {
            isUnloading: false,
            resolveError() {
                expect.step("resolve error");
            },
            triggerError() {},
        },
    });

    await userAgent.attemptReconnection(2);

    expect(userAgent.attemptingToReconnect).toBe(false);

    userAgent.attemptReconnection = (attemptCount) => expect.step(`retry ${attemptCount}`);
    const elapsedTime = await runAllTimers({ animationFrame: false });

    expect(elapsedTime >= 4000 && elapsedTime < 4500).toBe(true);
    expect.verifySteps(["reconnect", "register", "retry 3"]);
});
