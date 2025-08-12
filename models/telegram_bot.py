# -*- coding: utf-8 -*-
import logging
import requests
import json
import threading
from odoo import models, fields, api, registry, SUPERUSER_ID

_logger = logging.getLogger(__name__)

class TelegramBot(models.Model):
    _name = 'telegram.bot'
    _description = 'Telegram Bot Service'

    name = fields.Char('Bot Name', default='Telegram Task Bot')
    config_id = fields.Many2one('telegram.config', string='Configuration', required=True)
    is_running = fields.Boolean('Is Running', default=False)
    webhook_url = fields.Char('Webhook URL', help='URL for webhook (leave empty for polling)')
    
    def start_bot(self):
        """Start the Telegram bot"""
        if not self.config_id or not self.config_id.bot_token:
            raise ValueError("Bot token is required!")
            
        # Set webhook if URL provided
        if self.webhook_url:
            self._set_webhook()
        else:
            # Start polling in background
            self._start_polling()
            
        self.is_running = True
        _logger.info("Telegram bot started successfully")

    def stop_bot(self):
        """Stop the Telegram bot"""
        if self.webhook_url:
            self._remove_webhook()
        self.is_running = False
        _logger.info("Telegram bot stopped")

    def _set_webhook(self):
        """Set webhook for bot"""
        url = f"https://api.telegram.org/bot{self.config_id.bot_token}/setWebhook"
        data = {'url': self.webhook_url}
        response = requests.post(url, json=data)
        if response.ok:
            _logger.info("Webhook set successfully")
        else:
            _logger.error("Failed to set webhook: %s", response.text)

    def _remove_webhook(self):
        """Remove webhook"""
        url = f"https://api.telegram.org/bot{self.config_id.bot_token}/deleteWebhook"
        requests.post(url)

    def _start_polling(self):
        """Start polling for updates (background thread)"""
        def poll():
            offset = 0
            while self.is_running:
                try:
                    updates = self._get_updates(offset)
                    for update in updates:
                        self._process_update(update)
                        offset = update['update_id'] + 1
                except Exception as e:
                    _logger.error("Polling error: %s", e)
                    break
                    
        thread = threading.Thread(target=poll)
        thread.daemon = True
        thread.start()

    def _get_updates(self, offset=0):
        """Get updates from Telegram"""
        url = f"https://api.telegram.org/bot{self.config_id.bot_token}/getUpdates"
        params = {'offset': offset, 'timeout': 30}
        response = requests.get(url, params=params)
        if response.ok:
            return response.json().get('result', [])
        return []

    def _process_update(self, update):
        """Process single update"""
        # Use webhook controller logic
        from ..controllers.telegram_webhook import TelegramWebhook
        webhook = TelegramWebhook()
        
        # Simulate webhook data
        if 'message' in update:
            webhook._handle_message(update['message'])
        elif 'callback_query' in update:
            webhook._handle_callback_query(update['callback_query'])

    def send_task_notification(self, task_id):
        """Send task notification to user"""
        task = self.env['task.manager'].browse(task_id)
        if not task.exists() or not task.telegram_user_id or not task.telegram_user_id.telegram_id:
            return False
            
        text = f"📋 **New Task!**\n\n"
        text += f"**{task.title}**\n"
        if task.description:
            text += f"📝 {task.description}\n"
        if task.vehicle_id:
            text += f"🚗 Vehicle: {task.vehicle_id.name}\n"
        if task.deadline:
            text += f"⏰ Deadline: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"

        keyboard = {
            'inline_keyboard': [
                [{'text': '✅ Mark as Done', 'callback_data': f'task_done_{task.id}'}],
                [{'text': '📋 View All Tasks', 'callback_data': 'view_tasks'}],
                [{'text': '🏠 Main Menu', 'callback_data': 'main_menu'}]
            ]
        }
        
        return self._send_message(task.user_id.telegram_id, text, keyboard)

    def _send_message(self, chat_id, text, reply_markup=None):
        """Send message via Telegram API"""
        url = f"https://api.telegram.org/bot{self.config_id.bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
            
        try:
            response = requests.post(url, json=data)
            return response.ok
        except Exception as e:
            _logger.error("Error sending message: %s", e)
            return False
