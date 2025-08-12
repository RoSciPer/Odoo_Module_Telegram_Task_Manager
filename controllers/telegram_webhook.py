# -*- coding: utf-8 -*-
import logging
import json
from odoo import http, registry, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)

class TelegramWebhook(http.Controller):
    
    @http.route('/telegram/webhook', type='json', auth='none', methods=['POST'], csrf=False)
    def telegram_webhook(self, **kwargs):
        """Handle incoming Telegram webhook updates"""
        try:
            # Get update data
            update = request.httprequest.get_json(force=True)
            if not update:
                _logger.warning("Empty webhook update received")
                return {'ok': False, 'error': 'Empty update'}
            
            _logger.info(f"📨 Webhook update received: {json.dumps(update, indent=2)}")
            
            # Get database connection
            db_name = request.session.db or 'logistics_bot'
            
            with registry(db_name).cursor() as cr:
                from odoo import api
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                # Find active telegram service
                service = env['telegram.service'].search([('is_running', '=', True)], limit=1)
                if not service:
                    _logger.warning("No active telegram service found")
                    return {'ok': False, 'error': 'Service not running'}
                
                # Process the update
                try:
                    if 'message' in update:
                        _logger.info("📱 Processing message update")
                        service._handle_message(env, update['message'])
                    elif 'callback_query' in update:
                        _logger.info("🔘 Processing callback update")
                        service._handle_callback(env, update['callback_query'])
                    else:
                        _logger.info(f"ℹ️ Unhandled update type: {list(update.keys())}")
                    
                    # Commit the transaction
                    cr.commit()
                    
                    return {'ok': True}
                    
                except Exception as process_error:
                    _logger.error(f"❌ Error processing update: {process_error}")
                    cr.rollback()
                    return {'ok': False, 'error': str(process_error)}
                    
        except Exception as e:
            _logger.error(f"❌ Webhook error: {e}")
            return {'ok': False, 'error': str(e)}