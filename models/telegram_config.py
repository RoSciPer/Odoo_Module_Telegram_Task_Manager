# -*- coding: utf-8 -*-
import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class TelegramConfig(models.Model):
    _name = 'telegram.config'
    _description = 'Telegram Configuration'
    _inherit = ['mail.thread']

    name = fields.Char('Configuration Name', required=True, default='Default Config', tracking=True)
    bot_token = fields.Char('Bot Token', required=True, tracking=True)
    bot_username = fields.Char('Bot Username', readonly=True)
    admin_telegram_id = fields.Char('Admin Telegram ID', required=True, tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    
    # Status fields
    bot_status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('configured', 'Configured'),
        ('running', 'Running'),
        ('error', 'Error'),
    ], string='Bot Status', default='not_configured', readonly=True)
    
    last_error = fields.Text('Last Error', readonly=True)
    
    def test_connection(self):
        """Test bot connection"""
        self.ensure_one()
        if not self.bot_token:
            raise UserError(_('Bot token is required'))
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    bot_info = result['result']
                    self.write({
                        'bot_username': bot_info.get('username'),
                        'bot_status': 'configured',
                        'last_error': False
                    })
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success!'),
                            'message': _('Bot connection successful. Bot username: @%s') % bot_info.get('username'),
                            'type': 'success',
                        }
                    }
                else:
                    error_msg = result.get('description', 'Unknown error')
                    self.write({
                        'bot_status': 'error',
                        'last_error': error_msg
                    })
                    raise UserError(_('Bot API error: %s') % error_msg)
            else:
                error_msg = f'HTTP {response.status_code}: {response.text}'
                self.write({
                    'bot_status': 'error',
                    'last_error': error_msg
                })
                raise UserError(_('Connection failed: %s') % error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            self.write({
                'bot_status': 'error',
                'last_error': error_msg
            })
            raise UserError(_('Network error: %s') % error_msg)
    
    def start_service(self):
        """Start Telegram service"""
        self.ensure_one()
        if self.bot_status != 'configured':
            raise UserError(_('Please test connection first'))
        
        # Create or find service
        service = self.env['telegram.service'].search([
            ('bot_token', '=', self.bot_token)
        ], limit=1)
        
        if not service:
            service = self.env['telegram.service'].create({
                'name': f'Service for {self.name}',
                'bot_token': self.bot_token,
                'admin_telegram_id': self.admin_telegram_id
            })
        
        service.start_service()
        self.bot_status = 'running'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Service Started!'),
                'message': _('Telegram service has been started. Send /start to your bot!'),
                'type': 'success',
            }
        }
    
    def stop_service(self):
        """Stop Telegram service"""
        self.ensure_one()
        service = self.env['telegram.service'].search([
            ('bot_token', '=', self.bot_token)
        ], limit=1)
        
        if service:
            service.stop_service()
        
        self.bot_status = 'configured'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Service Stopped!'),
                'message': _('Telegram service has been stopped.'),
                'type': 'info',
            }
        }
