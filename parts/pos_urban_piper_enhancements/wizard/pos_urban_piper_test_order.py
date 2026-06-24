from odoo import models
from odoo.addons.pos_urban_piper_enhancements.controllers.main import PosUrbanPiperEnhancementController


class UrbanPiperTestOrderWizard(models.TransientModel):
    _inherit = 'pos.urbanpiper.test.order.wizard'

    def _get_urban_piper_controller(self):
        return PosUrbanPiperEnhancementController()
