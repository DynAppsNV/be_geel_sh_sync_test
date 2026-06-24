import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { floatIsZero, formatFloat, roundDecimals } from "@web/core/utils/numbers";
import { Reactive } from "@web/core/utils/reactive";

// This is functionally identical to the base ScaleService with `pos_iot` patch applied.
// Having a separate copy allows us to keep a certified version that will only change
// if absolutely necessary, whilst the base service is free to change.


export class CertifiedScaleService extends Reactive {
    constructor(env, deps) {
        super(...arguments);
        this.setup(env, deps);
    }

    setup(env, deps) {
        this.env = env;
        this.hardwareProxy = deps.hardware_proxy;
        this.lastWeight = null;
        this.weight = 0;
        this.iotHttpService = deps.hardware_proxy.iotHttp;
        this.reset();
    }

    start(errorCallback) {
        this.onError = errorCallback;
        if (!this.isManualMeasurement) {
            this.isMeasuring = true;
            this._readWeightContinuously();
        }
    }

    reset() {
        this.loading = false;
        this.isMeasuring = false;
        this.product = null;
        this.onError = null;
    }

    confirmWeight() {
        this.lastWeight = this.weight;
        return this.netWeight;
    }

    async readWeight() {
        this.loading = true;
        try {
            this.weight = await this._getWeightFromScale();
            this._clearLastWeightIfValid();
        } catch (error) {
            this.isMeasuring = false;
            this.onError?.(error.message);
        }
        this.loading = false;
    }

    async _getWeightFromScale() {
        return new Promise((resolve, reject) => {
            const { iotId, identifier } = this._scaleDevice;
            const callback = (data) => {
                try {
                    resolve(this._handleScaleMessage(data));
                } catch (error) {
                    reject(error);
                }
            };

            this.iotHttpService.action(
                iotId,
                identifier,
                { action: "read_once" },
                callback,
                () => {} // avoid timeout notification
            );
        });
    }

    async _readWeightContinuously() {
        const { iotId, identifier } = this._scaleDevice;
        const callback = (data) => {
            try {
                this.weight = this._handleScaleMessage(data);
                this._clearLastWeightIfValid();
            } catch (error) {
                this.onError?.(error.message);
            }
            if (this.isMeasuring) {
                this.iotHttpService.onMessage(iotId, identifier, callback, callback);
            }
        };
        this.iotHttpService.onMessage(iotId, identifier, callback, () => {});
        // there is not always an event waiting in the iot, so we trigger one
        this.iotHttpService.action(iotId, identifier, { action: "read_once" }, callback, () => {});
    }

    _handleScaleMessage(data) {
        if (data.status.status === "error") {
            throw new Error(`Cannot weigh product - ${data.status.message_body}`);
        } else if (data.status.status === "connected" || data.status === "success") {
            return data.result || 0;
        }
        // else, do nothing to avoid data.status === "error"
        // corresponding to timeout because weight did not change
        return this.weight;
    }

    setProduct(product, decimalAccuracy, unitPrice) {
        this.product = {
            name: product.display_name || _t("Unnamed Product"),
            unitOfMeasure: product.product_tmpl_id?.uom_id?.name || "kg",
            unitOfMeasureId: product.product_tmpl_id?.uom_id?.id,
            decimalAccuracy,
            unitPrice,
        };
    }

    _clearLastWeightIfValid() {
        if (this.lastWeight && this.isWeightValid) {
            this.lastWeight = null;
        }
    }

    get isWeightValid() {
        // LNE requires that the weight changes from the previously
        // added value before another product is allowed to be added.
        return (
            !this.lastWeight ||
            (!floatIsZero(this.lastWeight - this.weight, this.product.decimalAccuracy) &&
                this.netWeight > 0)
        );
    }

    get isManualMeasurement() {
        return this._scaleDevice?.manual_measurement;
    }

    get netWeight() {
        return roundDecimals(this.weight, this.product.decimalAccuracy);
    }

    get netWeightString() {
        const weightString = formatFloat(this.netWeight, {
            digits: [0, this.product.decimalAccuracy],
        });
        return `${weightString} ${this.product.unitOfMeasure}`;
    }

    get unitPriceString() {
        const priceString = this.env.utils.formatCurrency(this.product.unitPrice);
        return `${priceString} / ${this.product.unitOfMeasure}`;
    }

    get totalPriceString() {
        const priceString = this.env.utils.formatCurrency(this.netWeight * this.product.unitPrice);
        return priceString;
    }

    get _scaleDevice() {
        return this.hardwareProxy.deviceControllers.scale;
    }
}

const posScaleService = {
    dependencies: ["hardware_proxy"],
    start(env, deps) {
        return new CertifiedScaleService(env, deps);
    },
};

registry.category("services").add("pos_scale", posScaleService, { force: true });
