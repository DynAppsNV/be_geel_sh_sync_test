# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestPosPreparationDisplay(TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

    def test_load_preparation_display_model(self):

        config1 = self.env['pos.config'].create({
            'name': 'rest1',
            'active': False
        })
        config2 = self.env['pos.config'].create({
            'name': 'rest2'
        })
        config3 = self.env['pos.config'].create({
            'name': 'rest3'
        })
        config4 = self.env['pos.config'].create({
            'name': 'rest4'
        })

        # pos preperation display linked to specific configs
        display1 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 1',
            'pos_config_ids': [Command.link(config1.id)]
        })
        display2 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 2',
            'pos_config_ids': [Command.link(config2.id)]
        })
        display3 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 3',
            'pos_config_ids': []
        })
        display4 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 4',
            'pos_config_ids': [Command.link(config3.id)]
        })

        config2.open_ui()
        config3.open_ui()
        config4.open_ui()

        self.assertEqual({d['id'] for d in config2.current_session_id.load_data([])['pos.prep.display']},
                         {display1.id, display2.id, display3.id})
        self.assertEqual({d['id'] for d in config3.current_session_id.load_data([])['pos.prep.display']},
                         {display1.id, display3.id, display4.id})
        self.assertEqual({d['id'] for d in config4.current_session_id.load_data([])['pos.prep.display']},
                         {display1.id, display3.id})

    def test_preparation_updated_on_stage_change(self):
        prep_display = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 1',
            'pos_config_ids': [Command.link(self.config.id)],
        })
        first_stage, second_stage, final_stage = prep_display.stage_ids

        self.open_new_session()
        order = next(iter(self._create_orders([{'pos_order_lines_ui_args': [(self.product, 1)]}]).values()))
        order_line = order.lines[0]
        # Simulate sending the order to preparation
        self.env['pos.prep.order'].process_order(order.id)

        prep_line = self.env['pos.prep.line'].search([('pos_order_line_id', '=', order_line.id)])
        prep_state = self.env['pos.prep.state'].search([('prep_line_id', '=', prep_line.id)])
        self.assertEqual(prep_state.stage_id, first_stage)
        self.assertEqual(order_line.preparation_time, -1)
        self.assertEqual(order_line.service_time, -1)
        # Move order from first -> second stage
        prep_state.change_state_stage(
            {str(prep_state.id): second_stage.id},
            prep_display.id,
        )
        self.assertEqual(prep_state.stage_id, second_stage)
        self.assertNotEqual(order_line.preparation_time, -1)
        self.assertEqual(order_line.service_time, -1)
        # Move order from second -> final stage
        prep_state.change_state_stage(
            {str(prep_state.id): final_stage.id},
            prep_display.id,
        )
        self.assertEqual(prep_state.stage_id, final_stage)
        self.assertNotEqual(order_line.service_time, -1)
