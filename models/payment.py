from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date

class CustomPayment(models.Model):
    _name = 'custom.payment'
    _description = 'Custom Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Payment Reference', required=True, copy=False, readonly=True, default='New', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    amount = fields.Float(string='Amount', required=True, tracking=True)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # 1Stavno fields
    installments = fields.Integer(string='Number of Installments', default=1, tracking=True)
    stavno_transaction_id = fields.Char(string='1Stavno Transaction ID', tracking=True)
    stavno_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='1Stavno Status', default='pending', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('custom.payment') or 'New'
        return super(CustomPayment, self).create(vals)

    @api.constrains('amount')
    def _check_amount(self):
        for payment in self:
            if payment.amount <= 0:
                raise ValidationError("Payment amount must be greater than zero.")

    @api.constrains('payment_date')
    def _check_payment_date(self):
        for payment in self:
            if payment.payment_date > date.today():
                raise ValidationError("Payment date cannot be in the future.")

    @api.constrains('installments')
    def _check_installments(self):
        for payment in self:
            if payment.installments < 1:
                raise ValidationError("Number of installments must be at least 1.")

    def action_post(self):
        for payment in self:
            if payment.state != 'draft':
                raise UserError("Only payments in draft state can be posted.")
            if not payment.stavno_transaction_id:
                raise UserError("1Stavno payment must be processed before posting.")
            payment.write({'state': 'posted'})
            payment.message_post(body="Payment posted.")

    def action_cancel(self):
        for payment in self:
            if payment.state == 'posted':
                raise UserError("Posted payments cannot be cancelled.")
            payment.write({'state': 'cancelled'})
            payment.message_post(body="Payment cancelled.")

    def get_installments(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError("Amount must be greater than zero to get installments.")
        return self.env['stavno.api'].get_installments(self.amount)

    def process_stavno_payment(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("You can only process payments in draft state.")
        if self.stavno_status != 'pending':
            raise UserError("This payment has already been processed.")
        if self.amount <= 0:
            raise UserError("Payment amount must be greater than zero.")
        
        result = self.env['stavno.api'].process_payment(self)
        if result.get('Status') == 'Success':
            self.write({
                'stavno_status': 'approved',
                'stavno_transaction_id': result.get('TransactionId')
            })
            self.message_post(body=f"1Stavno payment processed successfully. Transaction ID: {self.stavno_transaction_id}")
        else:
            self.write({'stavno_status': 'rejected'})
            self.message_post(body=f"1Stavno payment processing failed. Reason: {result.get('Message')}")
        return result

class StavnoSettings(models.Model):
    _name = 'stavno.settings'
    _description = '1Stavno Settings'

    name = fields.Char(default='1Stavno Settings', readonly=True)
    api_key_test = fields.Char(string='Test API Key')
    api_key_production = fields.Char(string='Production API Key')
    test_url = fields.Char(string='Test URL', default='https://pktest.takoleasy.si')
    production_url = fields.Char(string='Production URL', default='https://pk.takoleasy.si')
    is_test_mode = fields.Boolean(string='Test Mode', default=True)
    display_installments = fields.Boolean(string='Display Installments', default=True)

    @api.model
    def get_stavno_settings(self):
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({})
        return settings

    @api.constrains('api_key_test', 'api_key_production')
    def _check_api_keys(self):
        for settings in self:
            if not settings.api_key_test or not settings.api_key_production:
                raise ValidationError("Both Test API Key and Production API Key must be provided.")