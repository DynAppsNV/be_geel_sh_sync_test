from psycopg2.extensions import AsIs

from odoo import api, exceptions, fields, models


class CustomFilter(models.Model):
    _name = "xx.dyn.custom.filter"
    _order = "sequence"
    _description = "Custom Filters for Dashboard"
    _rec_name = "filter_name"

    sequence = fields.Integer()
    dashboard_id = fields.Many2one("xx.dashboard")
    filter_name = fields.Char(required=True)
    wildcard = fields.Char()
    query_wildcard_replace = fields.Char(help="Replace if filter is empty")
    selection_ids_compute = fields.Boolean(default=False)
    selection_ids = fields.One2many(
        "xx.dyn.custom.filter.selection", "filter_id", compute="_compute_selections", store=True
    )
    manual_selection_ids = fields.One2many("xx.dyn.custom.filter.selection", "filter_id")
    use_odoo_data = fields.Boolean(help="If selected, the selection will be filled with Odoo data.")
    model_id = fields.Many2one("ir.model")
    model_field_name = fields.Many2one(
        "ir.model.fields", string="Field Name", domain="[('model_id', '=', model_id)]"
    )
    model_field_value = fields.Many2one(
        "ir.model.fields", string="Field Value", domain="[('model_id', '=', model_id)]"
    )
    query_threshold = fields.Integer(help="Set lower limit to use SQL query.", default=99999)
    multiselect = fields.Boolean(default=False)
    minimum_input_for_select = fields.Integer(default=0)
    hidden = fields.Boolean(string="Hide Filter", default=False)
    multicompany = fields.Boolean(default=False)

    @api.depends(
        "selection_ids_compute",
        "use_odoo_data",
        "manual_selection_ids",
        "model_id",
        "model_field_name",
        "model_field_value",
        "query_threshold",
        "multicompany",
    )
    def _compute_selections(self):
        if self.env.context.get("no_recompute"):
            return
        for rec in self:
            if not rec.use_odoo_data:
                rec.selection_ids = rec.manual_selection_ids
            elif not rec.selection_ids or self.env.context.get("force_recompute_selections"):
                if rec.model_id:
                    model = self.env[rec.model_id.model]
                    tablename = model._table
                    table_description = model._description

                    if (
                        "company_id" in model._fields
                        and model._fields["company_id"].store
                        and not rec.multicompany
                    ):
                        domain = [("company_id", "in", [False] + self.env.companies.ids)]
                        company_ids_csv = ", ".join([str(x) for x in self.env.companies.ids])
                        company_condition = (
                            f"where company_id is null or company_id in ({company_ids_csv})"
                        )
                    elif rec.model_id.model == "res.company" and not rec.multicompany:
                        domain = [("id", "in", [False] + self.env.companies.ids)]
                        company_ids_csv = ", ".join([str(x) for x in self.env.companies.ids])
                        company_condition = f"where id is null or id in ({company_ids_csv})"
                    else:
                        domain = []
                        company_condition = ""

                    model_records = self.env[rec.model_id.model].search(domain)
                    sel_values = list()
                    if len(model_records) > rec.query_threshold:
                        if not rec.model_field_name.store or not rec.model_field_value.store:
                            raise exceptions.UserError(
                                self.env._(
                                    "Field {rec.model_field_name.name} "
                                    "or {rec.model_field_value.name}"
                                    " is not stored in the database. "
                                    "Unable to use it in large selection list filters"
                                )
                            )

                        fieldname = rec.model_field_name.name
                        fieldvalue = rec.model_field_value.name
                        if rec.ids:
                            query = """select
                                            %s as filter_id,
                                            row_number() over (order by %s) as sequence,
                                            coalesce(%s,%s||' '||%s) as name,
                                            %s as value
                                       from %s %s"""
                            params = (
                                rec.ids[0],
                                AsIs(fieldvalue),
                                AsIs(fieldname),
                                table_description,
                                AsIs(fieldvalue),
                                AsIs(fieldvalue),
                                AsIs(tablename),
                                AsIs(company_condition),
                            )
                            self.env.cr.execute(query, params)
                            for val in self.env.cr.dictfetchall():
                                sel_values.append(
                                    (
                                        0,
                                        0,
                                        {
                                            "sequence": val["sequence"],
                                            "name": val["name"] if val["name"] else "-name-",
                                            "value": val["value"] if val["value"] else "-value-",
                                        },
                                    )
                                )
                    else:
                        sel_values = list()
                        for i in self.selection_ids.search([("filter_id", "=", rec.id)]).ids:
                            sel_values.append((2, i))
                        for i, data in enumerate(model_records):
                            sel_values.append(
                                (
                                    0,
                                    0,
                                    {
                                        "sequence": i,
                                        "name": rec.model_field_name.name
                                        and getattr(data, rec.model_field_name.name),
                                        "value": rec.model_field_value.name
                                        and getattr(data, rec.model_field_value.name),
                                    },
                                )
                            )
                        rec.selection_ids = sel_values or False
                else:
                    rec.selection_ids = False

    def open_self_one2many(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Dashboard Tile",
            "view_type": "form",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "current",
        }

    def unlink(self):
        """
        cascade delete since ondelete=cascade does not clear ir.model.data needed for importing
        dashboards
        """
        #        for rec in self:
        #            for selection in rec.selection_ids:
        #                selection.unlink()
        self.mapped("selection_ids").unlink()
        return super().unlink()

    def get_filter_selections(self, page, query):
        """Returns paginated selections matching query string"""
        results = []
        pagesize = 20
        selectfrom = (page - 1) * pagesize
        selectto = page * pagesize
        if not self.selection_ids:
            self.selection_ids_compute = not self.selection_ids_compute
        filtered_selections = (
            self.selection_ids.filtered(lambda x: query.upper() in x.name.upper())
            if query
            else self.selection_ids
        )
        for selection in filtered_selections[selectfrom:selectto]:
            results.append(selection.get_selection_values())
        return {
            "results": results,
            "more": len(filtered_selections) > selectto,
        }

    def get_selection_values(self, search_value):
        selections = self.selection_ids.filtered(lambda x: x.value == search_value)
        if selections:
            res = {"id": selections[0].value, "text": selections[0].name}
        else:
            res = False
        return res


class CustomFilterSelection(models.Model):
    _name = "xx.dyn.custom.filter.selection"
    _description = "Selection options for Custom Filters for Dashboard"
    _order = "sequence"

    filter_id = fields.Many2one("xx.dyn.custom.filter")
    sequence = fields.Integer(required=True)
    name = fields.Char(required=True)
    value = fields.Char(required=True)

    def get_selection_values(self):
        return {
            "id": self.value,
            "text": self.name,
        }


class CustomFilterValue(models.Model):
    _name = "xx.dyn.custom.filter.value"
    _description = "Custom Filter User Values for Dynapps Dashboard "

    user_id = fields.Many2one(comodel_name="res.users")
    filter_id = fields.Many2one(comodel_name="xx.dyn.custom.filter")
    value = fields.Char()

    def update_values(self, args):
        custom_filters = self.env.context.get("dynCustomFilters")
        for fltr in (
            list(filter(lambda x: "hidden" not in x or not x["hidden"], custom_filters)) or []
        ):
            filter_value = self.env["xx.dyn.custom.filter.value"].search(
                [("filter_id", "=", int(fltr["filter_id"])), ("user_id", "=", self.env.uid)]
            )
            filter_value_val = (
                isinstance(fltr["value"], list) and ",".join(fltr["value"]) or fltr["value"] or ""
            )

            if filter_value:
                filter_value.write({"value": filter_value_val})
            else:
                self.env["xx.dyn.custom.filter.value"].create(
                    {
                        "filter_id": fltr["filter_id"],
                        "user_id": self.env.uid,
                        "value": filter_value_val,
                    }
                )
