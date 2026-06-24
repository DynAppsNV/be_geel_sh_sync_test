import { patch } from "@web/core/utils/patch";
import { SampleServer } from "@web/model/sample_server";

/**
 * If `timer_start` is set, we see a bunch of running timers
 * which activate TimerHeader and thus when stopping timer in
 * another view makes it through tracebacks
 */
patch(SampleServer.prototype, {
    _generateFieldValue(modelName, fieldName, id) {
        if (fieldName === "timer_start") {
            return false;
        }
        return super._generateFieldValue(...arguments);
    },
});
