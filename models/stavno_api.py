import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class StavnoAPI(models.AbstractModel):
    _name = 'stavno.api'
    _description = '1Stavno API'

    @api.model
    def get_installments(self, amount):
        settings = self.env['stavno.settings'].get_stavno_settings()
        if settings.is_test_mode:
            url = f"{settings.test_url}/webpayment/rest/v1/creditapi/getInstallmentInfo/json"
            api_key = settings.api_key_test
        else:
            url = f"{settings.production_url}/webpayment/rest/v1/creditapi/getInstallmentInfo/json"
            api_key = settings.api_key_production

        data = {
            'APIKey': api_key,
            'CreditAmount': amount
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error fetching installment information: {str(e)}")

    @api.model
    def process_payment(self, payment):
        settings = self.env['stavno.settings'].get_stavno_settings()
        if settings.is_test_mode:
            url = f"{settings.test_url}/webpayment/rest/v1/creditapi/processPayment/json"
            api_key = settings.api_key_test
        else:
            url = f"{settings.production_url}/webpayment/rest/v1/creditapi/processPayment/json"
            api_key = settings.api_key_production

        data = {
            'APIKey': api_key,
            'CreditAmount': payment.amount,
            'Installments': payment.installments,
            'OrderId': payment.name,
            'CustomerName': payment.partner_id.name,
            'CustomerEmail': payment.partner_id.email,
            'CustomerPhone': payment.partner_id.phone,
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('Status') == 'Success':
                payment.write({
                    'stavno_transaction_id': result.get('TransactionId'),
                    'stavno_status': 'approved'
                })
            else:
                payment.write({
                    'stavno_status': 'rejected'
                })
                raise UserError(f"1Stavno payment processing failed: {result.get('Message')}")
            
            return result
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error processing 1Stavno payment: {str(e)}")

    @api.model
    def check_transaction_status(self, transaction_id):
        settings = self.env['stavno.settings'].get_stavno_settings()
        if settings.is_test_mode:
            url = f"{settings.test_url}/webpayment/rest/v1/creditapi/getTransactionStatus/json"
            api_key = settings.api_key_test
        else:
            url = f"{settings.production_url}/webpayment/rest/v1/creditapi/getTransactionStatus/json"
            api_key = settings.api_key_production

        data = {
            'APIKey': api_key,
            'TransactionId': transaction_id
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error checking transaction status: {str(e)}")

    @api.model
    def cron_check_pending_transactions(self):
        pending_payments = self.env['custom.payment'].search([
            ('stavno_status', '=', 'pending'),
            ('stavno_transaction_id', '!=', False)
        ])

        for payment in pending_payments:
            status = self.check_transaction_status(payment.stavno_transaction_id)
            if status.get('Status') == 'Success':
                payment.write({
                    'stavno_status': 'approved',
                    'state': 'posted'
                })
            elif status.get('Status') == 'Failed':
                payment.write({
                    'stavno_status': 'rejected',
                    'state': 'cancelled'
                })
            # If status is still pending, we don't change anything