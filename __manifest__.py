{
    'name': 'Summit 1stavno payment',
    'version': '13.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom payment module with 1Stavno integration for Odoo 13',
    'description': """
        This module adds custom payment functionality with 1Stavno integration to Odoo 13.
    """,
    'author': 'Marko Tomše',
    'website': 'https://www.tomse.eu',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_views.xml',
        'views/stavno_payment_report_views.xml',
        'data/cron.xml',
        #'report/stavno_payment_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}