import {DynDashboardArchParser} from "./dyn_dashboard_parser.esm";
import {DynDashboardController} from "./dyn_dashboard_controller.esm";
import {DynDashboardModel} from "./dyn_dashboard_model.esm";
import {DynDashboardRenderer} from "./dyn_dashboard_renderer.esm";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";

export const DynDashboardView = {
    type: "dyn_dashboard",
    display_name: _t("Dashboard"),
    icon: "fa-line-chart",
    multi_record: false,
    Controller: DynDashboardController,
    Renderer: DynDashboardRenderer,
    Model: DynDashboardModel,
    ArchParser: DynDashboardArchParser,
    searchMenuTypes: [],
    withSearchBar: false,
    withControlPanel: true,
    useSampleModel: false,
    resModel: "xx.dashboard",

    props(genericProps, view) {
        const {ArchParser} = view;
        const {arch} = genericProps;
        const archInfo = new ArchParser().parse(arch);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

registry.category("views").add("dyn_dashboard", DynDashboardView);
