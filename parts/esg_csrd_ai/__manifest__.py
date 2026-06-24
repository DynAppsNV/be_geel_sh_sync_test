{
    'name': "AI - ESG CSRD",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'AI integration with ESG CSRD',
    'depends': ['ai_app', 'esg_csrd'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_attachment_data.xml',
        'wizard/metrics_ai_generation_wizard_views.xml',
        'wizard/metrics_ai_suggestion_wizard_views.xml',
        'views/esg_metric_views.xml',
    ],
    'assets': {},
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
