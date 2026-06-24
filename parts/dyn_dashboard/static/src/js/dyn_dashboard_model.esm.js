import {KeepLast} from "@web/core/utils/concurrency";
import {loadBundle} from "@web/core/assets";
import {rpc} from "@web/core/network/rpc";

export class DynDashboardModel {
    constructor(orm, resModel, fields, archInfo, domain, context) {
        this.orm = orm;
        this.resModel = resModel;
        // We can access arch information parsed by the beautiful arch parser
        this.fields = fields;
        this.domain = domain;
        this.keepLast = new KeepLast();
        this.rpc = rpc;
        this.context = context;
        this.metaData = {};
    }

    async load() {
        await loadBundle("dyn_dashboard.jsLibs");
        var context = this.context;
        context.odoo_record_id = this.context.dashboard_id;
        this.dashboard_id = this.context.dashboard_id;
        this.dashboard_data = await this.rpc("/dyn_dashboard/get_dashboard_data", {
            context_to_pass: context,
            dashboard_id: this.dashboard_id,
        });
    }
}
