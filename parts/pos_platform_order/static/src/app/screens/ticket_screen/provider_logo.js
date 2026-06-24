import { Component, useState } from "@odoo/owl";

export class ProviderLogo extends Component {
    static template = "pos_platform_order.ProviderLogo";
    static props = {
        provider: { type: Object },
    };

    setup() {
        this.state = useState({
            src: this.props.provider.imageUrl,
        });
    }

    onLoadFailed() {
        this.state.src = "/web/static/img/placeholder.png";
    }
}
