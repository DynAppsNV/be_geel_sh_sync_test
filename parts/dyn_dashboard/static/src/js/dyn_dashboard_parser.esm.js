import {exprToBoolean} from "@web/core/utils/strings";
import {getActiveActions} from "@web/views/utils";

export class DynDashboardArchParser {
    parse(xmlDoc) {
        const disableAutofocus = exprToBoolean(
            xmlDoc.getAttribute("disable_autofocus") || ""
        );
        const activeActions = getActiveActions(xmlDoc);
        const fieldNodes = {};
        const widgetNodes = {};
        const autofocusFieldId = null;
        return {
            activeActions,
            autofocusFieldId,
            disableAutofocus,
            fieldNodes,
            widgetNodes,
            xmlDoc,
        };
    }
}
