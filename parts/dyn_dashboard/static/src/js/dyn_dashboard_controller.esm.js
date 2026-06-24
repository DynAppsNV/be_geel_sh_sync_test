import {Component, onWillStart, useState} from "@odoo/owl";
import {Layout} from "@web/search/layout";
import {useService} from "@web/core/utils/hooks";

export class DynDashboardController extends Component {
    static template = "DynDashboardView";
    setup() {
        this.orm = useService("orm");

        // The controller creates the model and make it reactive so whenever this.model is
        // accessed and edited then it'll cause a rerendering
        this.model = useState(
            new this.props.Model(
                this.orm,
                this.props.resModel,
                this.props.fields,
                this.props.archInfo,
                this.props.domain,
                this.props.context
            )
        );

        onWillStart(async () => {
            await this.model.load();
        });
    }
}

DynDashboardController.template = "dyn_dashboard.DynDashboardView";
DynDashboardController.components = {Layout};
