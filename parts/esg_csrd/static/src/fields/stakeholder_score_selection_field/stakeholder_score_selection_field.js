import { registry } from "@web/core/registry";
import {
    SelectionField,
    selection_field as selectionField,
} from "@web/views/fields/selection/selection_field";

export class StakeholderScoreSelectionField extends SelectionField {
    static props = {
        ...SelectionField.props,
        relatedFieldName: { type: String, optional: false },
    };

    onChange(value) {
        super.onChange(value);
        const relatedFieldName = this.props.relatedFieldName;
        if (
            !this.props.record.data[relatedFieldName] &&
            this.props.record.data[this.props.name] !== value
        ) {
            this.props.record.update({ [relatedFieldName]: true });
        }
    }
}

registry.category("fields").add("stakeholder_score_selection", {
    ...selectionField,
    component: StakeholderScoreSelectionField,
    extractProps: ({ options }) => ({
        relatedFieldName: options.related_field_name,
    }),
});
