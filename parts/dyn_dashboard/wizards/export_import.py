import base64
import logging
import os
from datetime import datetime

from lxml import etree as ET

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    import arrow
except (OSError, ImportError) as err:  # pragma: no cover
    _logger.debug(err)

MODELS2SKIP = ["base."]
FIELDS2SKIP = {"xx.dyn.custom.filter": []}


class DynExportItems(models.TransientModel):
    _name = "xx.export.items"
    _description = "DynApps Dashboard Export"
    _rec_name = "name"

    name = fields.Char("Item Name")
    res_id = fields.Integer("Item Id")
    wizard_id = fields.Many2one("xx.dashboard.export.wizard", ondelete="cascade")


class DynDashboardExportWizard(models.TransientModel):
    _name = "xx.dashboard.export.wizard"
    _description = "DynApps Dashboard Export"
    _rec_name = "name"

    name = fields.Char("Export File Prefix", default="Export Dashboard")
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        default=lambda self: self.env["ir.model"]
        .sudo()
        .search([("model", "=", "xx.dashboard")], limit=1),
        help="The model object to export",
    )
    export_items = fields.Many2many(
        string="Selected Items To Export",
        comodel_name="xx.export.items",
        domain="[('wizard_id', '=', id)]",
    )
    filename = fields.Char(default="export_dashboard.xml")
    filecontent = fields.Binary()
    action_log = fields.Text("Import / Export Log")
    import_status = fields.Selection([("stopped", "Stopped"), ("running", "Running")])

    def export_dashboard_config(self):
        wizard = self.create({})
        view = self.env.ref("dyn_dashboard.dyn_dashboard_export_wizard_form_view")
        action = {
            "name": self.env._("Dashboard Export"),
            "view_mode": "form",
            "view_id": view.id,
            "view_type": "form",
            "res_model": "xx.dashboard.export.wizard",
            "res_id": wizard.id,
            "type": "ir.actions.act_window",
            "target": "current",
        }
        return action

    @api.onchange("export_items")
    def _onchange_export_items(self):
        self.filename += self.get_filename_suffix()

    def _get_export_items(self):
        """Get list of model items.

        :return [(model, name), ...]:
            Tuple list of available instances.
        """
        domain = []
        model = self.model_id and self.model_id.model or "xx.dashboard"
        res = [(m.id, m.name) for m in self.env[model].search(domain)]
        return res

    def _rebuild_export_items_pool(self):
        """
        Rebuilds the pool of export items for the wizard. This method ensures that
        the relevant export items associated with the wizard are accurately updated
        based on the current model and its respective records.

        Summary:
        - Removes unlinked export items specific to the wizard to prevent cross-test interference.
        - Populates export items for the wizard model, associating records with their
          respective IDs and names.

        :return: None
        :rtype: NoneType
        """
        for wizard in self:
            if not wizard.export_items:
                # Only touch items of *this* wizard to avoid cross-test interference.
                wizard.env["xx.export.items"].search([("wizard_id", "=", False)]).unlink()

            if not wizard.model_id:
                continue

            Model = wizard.env[wizard.model_id.model]
            for item in Model.search([("name", "!=", False)]):
                wizard.env["xx.export.items"].create(
                    {
                        "wizard_id": wizard.id,
                        "res_id": item.id,
                        "name": item.name,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        wizards._rebuild_export_items_pool()
        return wizards

    @api.onchange("model_id")
    def _onchange_model_id(self):
        """Odoo’s Form helper does not simulate the web client’s “onload onchange for defaulted
        fields” behavior in the same way.  In the real UI, when the wizard opens, the client does
        a default_get and then runs onchanges to compute dependent fields (that’s why your manual
        test “works”). In many automated cases, unless you change the field inside Form, the
        onchange isn’t invoked.  So: with a readonly + defaulted model_id, your _onchange_model_id
        is a poor hook for “initialization” logic. It’s a UI convenience hook, not a reliable
        initializer.  For 'manual selection', the clean way is to not use onchange for
        initialization at all. Build the pool of xx.export.items when the wizard is created (or
        when the form is opened via default_get), then let the user pick manually."""
        # Keep it for UI when/if model_id ever becomes editable,
        # but don't rely on it for initialization.
        self._rebuild_export_items_pool()

    def get_filename_suffix(self):
        model = self.model_id and self.model_id.model or "xx.dashboard"
        parts = []
        for x in self.export_items:
            rec = self.env[model].browse(x.res_id)
            name = rec.name or ""
            if name:
                parts.append(name)
        return "".join(f"-{p}" for p in parts)

    def write_log(self, msg):
        msg = f"{datetime.now()} : {msg}"
        self.action_log = self.action_log + "\n" + msg if self.action_log else msg

    def import_xmlfile(self):
        self.write_log(f"Start Import '{self.filename}'.")
        filecontent = base64.b64decode(self.filecontent)
        etree = ET.fromstring(filecontent)
        self.import_xml(etree)
        self.write_log(f"End Import '{self.filename}'.")
        self.ensure_one()
        return {
            "context": self.env.context,
            "view_type": "form",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "view_id": False,
            "type": "ir.actions.act_window",
            "target": "new",
        }

    @api.model
    def get_xmlid_tag(self, record, xmlid=False):
        """Get external ID of the record, if not already exists create one"""

        def get_key():
            element = False
            while not ET.iselement(element):
                technical_key = base64.standard_b64encode(os.urandom(12)).decode()
                try:
                    element = ET.Element(technical_key)
                except ValueError:
                    continue
            return technical_key

        module, name = (
            tuple(xmlid.split("."))
            if xmlid
            else tuple(["__import__", f"{record._table}_{get_key()}"])
        )

        ModelData = self.env["ir.model.data"]
        external_id = record.get_external_id()
        if not external_id or (record.id in external_id and external_id[record.id] == ""):
            vals = {
                "name": name,
                "module": module,
                "model": record._name,
                "res_id": record.id,
            }
            data = ModelData.search([("name", "=", xmlid), ("model", "=", record._name)])
            if data:
                data.write(vals)
            else:
                ModelData.create(vals)
            external_id = record.get_external_id()
        res = external_id[record.id]
        return res

    def export_model_data(self, Model, ids=False):
        processed_objects = list()

        def model_data(parent, obj, external_id=False):
            if obj in processed_objects or obj._name in ["ir.model"]:  # avoid recursion
                return False
            processed_objects.append(obj)
            obj_fields = obj.fields_get()
            for field, field_attrs in obj_fields.items():
                if field_attrs.get("readonly") and not field_attrs.get("store"):
                    continue
                if obj._name in FIELDS2SKIP and field in FIELDS2SKIP[obj._name]:
                    continue
                element = ET.SubElement(parent, field)
                if field_attrs["type"] in ["one2many", "many2one"]:
                    value = ""
                    element.attrib["type"] = field_attrs["type"]
                    for related_obj in obj[field]:
                        external_id = self.get_xmlid_tag(related_obj)
                        if external_id:
                            subelement = ET.SubElement(element, external_id)
                            if not any(i in external_id for i in MODELS2SKIP) and (
                                related_obj._module == self._module
                                or related_obj._original_module == self._module
                            ):
                                model_data(subelement, related_obj, external_id=external_id)

                elif field_attrs["type"] == "datetime":
                    element.attrib["type"] = field_attrs["type"]
                elif field_attrs["type"] == "date":
                    element.attrib["type"] = field_attrs["type"]
                    value = obj[field] and obj[field] or ""
                elif field_attrs["type"] == "boolean":
                    element.attrib["type"] = field_attrs["type"]
                    value = obj[field]
                elif field_attrs["type"] == "integer":
                    element.attrib["type"] = field_attrs["type"]
                    value = obj[field] and obj[field] or ""
                else:
                    value = obj[field] and obj[field] or ""
                element.text = str(value)

        document = ET.Element("data")
        if "drill_hierarchy" in Model._fields and Model._fields["drill_hierarchy"].store:
            order = "drill_hierarchy, id"
        else:
            order = "id"
        for obj in Model.search([("id", "in", ids)], order=order):
            external_id = self.get_xmlid_tag(obj)
            model_element = ET.SubElement(document, external_id)
            model_data(model_element, obj)

        res = ET.tostring(document, pretty_print=True, xml_declaration=True, encoding="utf-8")
        return res

    def export_xml(self):
        self.write_log("Start Export")

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        Model = self.env["xx.dashboard"]
        action = self._get_records_action()
        if self.export_items:
            for item in self.export_items:
                Model.clear_filter_selections(item.res_id)
                obj_name = Model.search([("id", "=", item.res_id)]).name
                self.write_log(f"Exporting {obj_name}")
            datas = self.export_model_data(Model, [x.res_id for x in self.export_items])
            attachment = self.env["ir.attachment"].create(
                {
                    "name": self.name + self.get_filename_suffix(),
                    "mimetype": "text/xml",
                    "datas": base64.b64encode(datas),
                }
            )

            self.write_log(f"End Export {obj_name}")
            action.update(
                {
                    "type": "ir.actions.act_url",
                    "url": f"{base_url}/web/content/{attachment.id}?download=true",
                }
            )
            return action

        action.update({"target": "new"})
        self.write_log("No items selected to export")
        return action

    @api.onchange("action_log")
    def onchange_action_log(self):
        _logger.debug("action_log changed")

    def import_xml(self, xml_root):
        dashboard_ids = dict()
        for element in xml_root:
            dashboard_dict = self.etree2dict(element)
            for xmlid in dashboard_dict.keys():
                data = dashboard_dict[xmlid]
                dashboard_data, external_ids = self.prepare_data(data)
                try:
                    obj = self.env.ref(xmlid)
                except ValueError:
                    obj = False
                self.write({"import_status": "running"})
                if obj:
                    obj.write(dashboard_data)
                else:
                    Model = self.env[".".join(xmlid.split(".")[1].split("_")[:-1])]
                    obj = Model.create(dashboard_data)
                    xmlid = self.get_xmlid_tag(obj, xmlid)

                if obj:
                    dashboard_ids[xmlid] = obj
                self.update_new_ids(external_ids)
        return dashboard_ids

    def record_res_id(self, *args):
        res_id = 0
        model, vals = args
        recname = self.env[model]._rec_name
        if recname in vals and model not in ["ir.act.window"]:
            domain = [(recname, "=", vals[recname])]
            searchfields = []
            for fieldname, attrs in self.env[model].fields_get().items():
                if (
                    fieldname in vals
                    and vals[fieldname]
                    and attrs["type"] == "many2one"
                    and fieldname not in ("create_uid", "write_uid")
                ):
                    searchfields.append((fieldname, "=", vals[fieldname]))
            obj_ids = self.env[model].search(domain + searchfields, order="id desc")
            res_id = obj_ids[0].id
        return res_id

    def update_new_ids(self, external_ids):
        for external_id, vals in external_ids.items():
            module, name = external_id.split(".")
            model = name.rsplit("_", 1)[0].replace("_", ".")
            res_id = self.record_res_id(model, vals)
            if res_id:
                self.env["ir.model.data"].create(
                    {
                        "model": model,
                        "res_id": res_id,
                        "module": module,
                        "name": name,
                    }
                )

    # converts an etree to dict, useful to convert xml to dict
    def etree2dict(self, tree):
        root, contents = self.recursive_dict(tree)
        return {root: contents} if contents else dict()

    def recursive_dict(self, element):
        if element.attrib and "type" in element.attrib and element.attrib["type"] == "one2many":
            child_values = dict()
            for child in element:
                child_dict = dict(map(self.recursive_dict, child)) or self.getElementValue(child)
                child_values.update({child.tag: child_dict})
            return element.tag, child_values

        elif element.attrib and "type" in element.attrib and element.attrib["type"] == "many2one":
            item_values = tuple()
            for item in element:
                child_values = dict()
                for child in item:
                    child_dict = dict(map(self.recursive_dict, child)) or self.getElementValue(
                        child
                    )
                    child_values.update({child.tag: child_dict})
                item_values = (item.tag, child_values)
            return element.tag, item_values

        else:
            res = dict(map(self.recursive_dict, element)) or self.getElementValue(element)
            return element.tag, res

    def getElementValue(self, element):
        if element.text:
            if element.attrib and "type" in element.attrib:
                attr_type = element.attrib.get("type")
                if attr_type == "integer":
                    return len(element.text.strip()) > 0 and int(element.text.strip())
                if attr_type == "float":
                    return len(element.text.strip()) > 0 and float(element.text.strip())
                if attr_type == "boolean":
                    return element.text.lower().strip() == "true"
                if attr_type == "date":
                    return (
                        len(element.text.strip()) > 0
                        and arrow.get(element.text.strip()).timestamp()
                    )
            else:
                return element.text.strip()
        elif element.attrib:
            if "nil" in element.attrib:
                return None
        else:
            return None

    def prepare_data(self, data):
        remove_fields = list()
        external_ids = dict()
        for field in data:
            if isinstance(data[field], dict):  # one2many
                if data[field]:
                    o2m = []
                    for child in data[field].keys():
                        vals = dict()
                        try:
                            res_id = self.env.ref(child).id if child else 0
                        except ValueError:
                            res_id = 0
                        if data[field][child]:
                            vals, xids = self.prepare_data(data[field][child])
                            external_ids.update(xids)

                        if res_id:
                            o2m_line = (1, res_id, vals) if vals else (4, res_id)
                            o2m.append(o2m_line)
                        else:
                            if vals:
                                o2m_line = (0, 0, vals)
                                o2m.append(o2m_line)
                                external_ids.update({child: vals})

                    data[field] = o2m
                else:
                    remove_fields.append(field)
            elif isinstance(data[field], tuple):  # many2one
                if data[field]:
                    xmlid, vals = data[field]
                    try:
                        res_id = self.env.ref(xmlid).id if xmlid else 0
                    except ValueError:
                        res_id = 0
                    if res_id:
                        data[field] = res_id
                    else:
                        data[field] = False
                else:
                    remove_fields.append(field)

        for field in remove_fields:
            del data[field]
        return data, external_ids

    class DynDashboardTile(models.Model):
        _inherit = "xx.dashboard.tile"

        @api.depends("query")
        def _compute_query(self):
            wizard = self.env["xx.dashboard.export.wizard"].search(
                [("import_status", "=", "running")]
            )
            if len(wizard) > 0:
                wizard.write({"import_status": "stopped"})
            else:
                super()._compute_query()
            return
