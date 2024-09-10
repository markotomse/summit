from odoo import api, fields, models, tools

class StavnoPaymentReport(models.Model):
    _name = 'stavno.payment.report'
    _description = '1Stavno Payment Report'
    _auto = False

    name = fields.Char(string='Payment Reference')
    partner_id = fields.Many2one('res.partner', string='Customer')
    amount = fields.Float(string='Amount')
    payment_date = fields.Date(string='Payment Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status')
    installments = fields.Integer(string='Number of Installments')
    stavno_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='1Stavno Status')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.name AS name,
                    p.partner_id AS partner_id,
                    p.amount AS amount,
                    p.payment_date AS payment_date,
                    p.state AS state,
                    p.installments AS installments,
                    p.stavno_status AS stavno_status
                FROM custom_payment p
            )
        """ % self._table)

class StavnoPaymentReportWizard(models.TransientModel):
    _name = 'stavno.payment.report.wizard'
    _description = '1Stavno Payment Report Wizard'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer')
    stavno_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='1Stavno Status')

    def action_generate_report(self):
        domain = [
            ('payment_date', '>=', self.date_from),
            ('payment_date', '<=', self.date_to)
        ]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.stavno_status:
            domain.append(('stavno_status', '=', self.stavno_status))

        report_data = self.env['stavno.payment.report'].search(domain)

        return {
            'name': '1Stavno Payment Report',
            'type': 'ir.actions.act_window',
            'res_model': 'stavno.payment.report',
            'view_mode': 'tree,graph,pivot',
            'domain': domain,
        }