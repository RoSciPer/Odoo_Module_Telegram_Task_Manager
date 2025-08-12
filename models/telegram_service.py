# -*- coding: utf-8 -*-
import logging
import requests
import json
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class TelegramService(models.Model):
    _name = 'telegram.service' 
    _description = 'Telegram Service Manager'

    name = fields.Char('Service Name', default='Telegram Bot Service')
    bot_token = fields.Char('Bot Token', required=True)
    admin_telegram_id = fields.Char('Admin Telegram ID', required=True)
    is_running = fields.Boolean('Is Running', default=False)
    auto_start = fields.Boolean('Auto Start on Server Start', default=True, help='Automatically start webhook when Odoo server starts')
    last_update_id = fields.Integer('Last Update ID')  # OBLIGĀTI PIEVIENO ŠO LAUKU!

    @api.model
    def _auto_start_service(self):
        try:
            service = self.search([('auto_start', '=', True)], limit=1)
            if service and service.bot_token and service.admin_telegram_id:
                if not service.is_running:
                    _logger.info("🚀 Auto-starting Telegram webhook service...")
                    service.start_service()
                    startup_msg = (
                        f"🔄 **Odoo Server Started**\n\n"
                        f"✅ Telegram Bot is active\n"
                        f"🌐 Webhook is working\n"
                        f"🕐 Time: {fields.Datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                        f"🔗 Database connection restored"
                    )
                    service._send_message(service.admin_telegram_id, startup_msg)
                    _logger.info("✅ Telegram webhook service auto-started and admin notified")
                else:
                    _logger.info("ℹ️ Telegram service already running")
            else:
                _logger.warning("⚠️ No auto-start service configured or missing bot token/admin ID")
        except Exception as e:
            _logger.error(f"❌ Error auto-starting Telegram service: {e}")

    def start_service(self):
        if self.is_running:
            _logger.info("Service already running")
            return
        if not self.bot_token:
            raise ValueError("Bot token is required!")
        _logger.info("Starting Telegram service with webhook...")
        self._setup_webhook()
    
    def _setup_webhook(self):
        try:
            webhook_url = "https://bidsolana.xyz/telegram/webhook"
            url = f"https://api.telegram.org/bot{self.bot_token}/setWebhook"
            data = {
                'url': webhook_url,
                'allowed_updates': ['message', 'callback_query']
            }
            response = requests.post(url, json=data, timeout=10)
            if response.ok:
                result = response.json()
                if result.get('ok'):
                    self.is_running = True
                    _logger.info(f"✅ Webhook set successfully: {webhook_url}")
                    if self.admin_telegram_id:
                        startup_msg = (
                            f"🔄 **Odoo Server Started**\n\n"
                            f"✅ Telegram Bot is active\n"
                            f"🌐 Webhook is working\n"
                            f"🔗 URL: {webhook_url}\n"
                            f"🕐 Time: {fields.Datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                        )
                        self._send_message(self.admin_telegram_id, startup_msg)
                else:
                    error_desc = result.get('description', 'Unknown error')
                    _logger.error(f"❌ Failed to set webhook: {error_desc}")
            else:
                _logger.error(f"❌ HTTP error setting webhook: {response.status_code}")
        except Exception as e:
            _logger.error(f"❌ Error setting up webhook: {e}")
            self.is_running = False
            
    
    def stop_service(self):
        """Stop Telegram service by removing webhook"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/deleteWebhook"
            response = requests.post(url, timeout=10)
            
            if response.ok:
                _logger.info("✅ Webhook removed successfully")
            else:
                _logger.error(f"❌ Failed to remove webhook: {response.status_code}")
                
            self.is_running = False
            _logger.info("🛑 Telegram service stopped")
            
        except Exception as e:
            _logger.error(f"❌ Error stopping service: {e}")
            self.is_running = False

    def _handle_message(self, env, message):
        """Handle incoming message from webhook"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user_id = message['from']['id']
        username = message['from'].get('username', '')
        first_name = message['from'].get('first_name', 'Unknown')
        
        _logger.info("📨 MESSAGE RECEIVED:")
        _logger.info(f"   User: {first_name} (@{username}) ID: {user_id}")
        _logger.info(f"   Chat: {chat_id}")
        _logger.info(f"   Text: '{text}'")
        
        # Get or create user
        telegram_user = self._get_or_create_user(env, user_id, username, first_name)
        _logger.info(f"👤 Telegram user: {telegram_user.name} (Admin: {telegram_user.is_admin})")
        
        # Handle photo messages for reports
        if 'photo' in message:
            _logger.info("📸 Photo message received")
            self._handle_photo_report(env, message, telegram_user)
            return
        
        # Handle text commands
        if text == '/start':
            _logger.info("🚀 Processing /start command")
            self._send_welcome(env, chat_id, telegram_user)
        elif text == '/tasks' or 'uzdevumi' in text.lower():
            _logger.info("📋 Processing /tasks command")
            self._send_tasks(env, chat_id, telegram_user)
        elif text == '/menu':
            _logger.info("📱 Processing /menu command")
            self._send_menu(env, chat_id)
        elif text == '/debug':
            _logger.info("🔧 Processing /debug command")
            debug_msg = f"🔧 **Debug Info:**\n\n"
            debug_msg += f"✅ **Bot Status:** Working!\n"
            debug_msg += f"👤 **User:** {first_name}\n"
            debug_msg += f"🆔 **User ID:** `{user_id}`\n"
            debug_msg += f"💬 **Chat ID:** `{chat_id}`\n"
            debug_msg += f"🏷️ **Username:** @{username or 'none'}\n"
            debug_msg += f"👑 **Admin:** {'Yes' if telegram_user.is_admin else 'No'}\n"
            debug_msg += f"🕐 **Time:** {fields.Datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            debug_msg += f"🌐 **Webhook:** Active\n"
            debug_msg += f"🔗 **Database:** Connected"
            
            self._send_message(chat_id, debug_msg)
            _logger.info("🔧 Debug info sent successfully")
        elif text == '/help':
            _logger.info("❓ Processing /help command")
            help_msg = f"🤖 **Telegram Task Manager**\n\n"
            help_msg += f"📋 **Commands:**\n"
            help_msg += f"/start - Start\n"
            help_msg += f"/tasks - Show Tasks\n"
            help_msg += f"/menu - Main Menu\n"
            help_msg += f"/debug - System Check\n"
            help_msg += f"/status - Admin Status\n"
            help_msg += f"/help - This Help\n\n"
            help_msg += f"💡 **Tip:** Type any message to report an issue!"
            
            self._send_message(chat_id, help_msg)
        elif text == '/status' and telegram_user.is_admin:
            _logger.info("📊 Processing /status command for admin")
            status_msg = f"📊 **Admin Status Report**\n\n"
            
            user_count = env['telegram.user'].search_count([('active', '=', True)])
            admin_count = env['telegram.user'].search_count([('is_admin', '=', True)])
            
            total_tasks = env['task.manager'].search_count([])
            active_tasks = env['task.manager'].search_count([('state', 'in', ['draft', 'in_progress'])])
            status_msg += f"👥 **Users:** {user_count} (admins: {admin_count})\n"
            status_msg += f"📋 **Tasks:** {active_tasks} active / {total_tasks} total\n"
            status_msg += f"🤖 **Admin ID:** `{self.admin_telegram_id}`\n"
            status_msg += f"👤 **Your ID:** `{user_id}`\n"
            status_msg += f"🌐 **Webhook:** {'✅ Active' if self.is_running else '❌ Stopped'}\n"
            status_msg += f"🕐 **Time:** {fields.Datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"

            self._send_message(chat_id, status_msg)
        else:
            # Handle as report (if not admin)
            if not telegram_user.is_admin:
                _logger.info("📝 Treating message as report from regular user")
                _logger.info(f"📝 USER MESSAGE RECEIVED: '{text}' from {telegram_user.name}")
                self._handle_report(env, chat_id, telegram_user, text)
            else:
                _logger.info("👑 Admin message - ignoring to prevent echo")
                _logger.info(f"👑 ADMIN MESSAGE: '{text}' from {telegram_user.name}")

    def _handle_callback(self, env, callback_query):
        """Handle button callbacks with detailed logging and proper responses"""
        try:
            chat_id = callback_query['message']['chat']['id']
            data = callback_query['data']
            callback_id = callback_query['id']
            user_id = callback_query['from']['id']
            user_name = callback_query['from'].get('first_name', 'Unknown')
            
            telegram_user = env['telegram.user'].search([('telegram_id', '=', str(user_id))], limit=1)
            
            _logger.info("📱 CALLBACK RECEIVED:")
            _logger.info(f"   User: {user_name} (ID: {user_id})")
            _logger.info(f"   Data: {data}")
            _logger.info(f"   Chat ID: {chat_id}")
            _logger.info(f"   Callback ID: {callback_id}")

            response_text = "✅ Confirmed"
            show_alert = False
            
            if data.startswith('done_'):
                task_id = int(data.split('_')[1])
                _logger.info(f"🎯 Marking task {task_id} as done")
                result = self._mark_task_done(env, chat_id, task_id, telegram_user)
                response_text = "✅ Task Completed!" if result else "❌ Error"
                show_alert = True
                
            elif data.startswith('vehicle_info_'):
                vehicle_id = int(data.split('_')[2])
                _logger.info(f"🚗 Showing vehicle info for {vehicle_id}")
                self._send_vehicle_info(env, chat_id, vehicle_id)
                response_text = "ℹ️ Vehicle Information"
                
            elif data == 'tasks':
                _logger.info(f"📋 Showing tasks for user")
                self._send_tasks(env, chat_id, telegram_user)
                response_text = "📋 Tasks"
                
            elif data == 'report':
                _logger.info(f"⚠️ Report prompt requested")
                self._send_report_prompt(env, chat_id)
                response_text = "⚠️ Reporting Mode"
                
            elif data == 'menu':
                _logger.info(f"📱 Main menu requested")
                self._send_menu(env, chat_id)
                response_text = "📱 Main Menu"
                
            elif data == 'restart_service':
                _logger.info(f"🔄 Service restart requested by {user_name}")
                if telegram_user and telegram_user.is_admin:
                    service = env['telegram.service'].browse(self.id)
                    service.stop_service()
                    service.start_service()
                    response_text = "🔄 Service restarted!"
                    show_alert = True
                else:
                    response_text = "❌ Admin only"
                    show_alert = True
                
            elif data.startswith('set_day_'):
                task_id = int(data.split('_')[2])
                _logger.info(f"🗓️ User wants to set execution day for task {task_id}")
                self._ask_for_execution_day(chat_id, task_id)
                response_text = "🗓️ Please enter the day you can complete the task!"
                show_alert = True
                
            else:
                _logger.warning(f"❓ Unknown callback data: {data}")
                response_text = "❓ Unknown command"
                show_alert = True
                
            # CRITICAL: Always answer the callback
            self._answer_callback(callback_id, response_text, show_alert)
            _logger.info(f"✅ Callback answered with: {response_text}")
            
        except Exception as e:
            error_msg = f"❌ Callback error: {e}"
            _logger.error(error_msg)
            try:
                self._answer_callback(callback_query.get('id', ''), "❌ System Error", True)
                _logger.info(f"⚠️ Error callback answered")
            except Exception as answer_error:
                _logger.error(f"💥 Failed to answer error callback: {answer_error}")

    def _get_or_create_user(self, env, user_id, username, first_name):
        """Get or create telegram user with admin notification"""
        user = env['telegram.user'].search([('telegram_id', '=', str(user_id))], limit=1)
        if not user:
            user = env['telegram.user'].create({
                'name': first_name or username or f'User_{user_id}',
                'telegram_id': str(user_id),
                'username': username,
                'is_admin': str(user_id) == self.admin_telegram_id,
                'active': True
            })
            
            if self.admin_telegram_id and str(user_id) != self.admin_telegram_id:
                admin_text = f"👤 **New user joined!**\n\n"
                admin_text += f"🆔 **ID:** `{user_id}`\n"
                admin_text += f"👤 **Name:** {first_name or 'Not specified'}\n"
                admin_text += f"🏷️ **Username:** @{username or 'none'}\n"
                admin_text += f"🕐 **Time:** {fields.Datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                admin_text += f"ℹ️ User can now receive tasks."
                
                self._send_message(self.admin_telegram_id, admin_text)
                _logger.info(f"✅ Admin notified about new user: {user.name}")
                
        return user

    def _send_welcome(self, env, chat_id, user):
        """Send welcome message"""
        text = f"Hello, {user.name}! 👋\n\nTelegram Task Manager bots.\n\nPlease choose:"
        keyboard = [
            [{'text': '📋 Mani uzdevumi', 'callback_data': 'tasks'}],
            [{'text': '⚠️ Ziņot problēmu', 'callback_data': 'report'}],
            [{'text': '📱 Izvēlne', 'callback_data': 'menu'}]
        ]
        self._send_message(chat_id, text, keyboard)

    def _send_menu(self, env, chat_id):
        """Send main menu"""
        text = "📱 Main Menu:"
        keyboard = [
            [{'text': '📋 Tasks', 'callback_data': 'tasks'}],
            [{'text': '⚠️ Report Issue', 'callback_data': 'report'}],
            [{'text': '📱 Main Menu', 'callback_data': 'menu'}]
        ]
        self._send_message(chat_id, text, keyboard)

    def _send_vehicle_info(self, env, chat_id, vehicle_id):
        """Send detailed vehicle information"""
        vehicle = env['task.vehicle'].browse(vehicle_id)
        if not vehicle.exists():
            self._send_message(chat_id, "❌ Vehicle not found.")
            return
            
        text = f"🚗 **{vehicle.name}**\n\n"
        
        if vehicle.license_plate:
            text += f"🔢 License Plate: **{vehicle.license_plate}**\n"

        if vehicle.driver_name:
            text += f"👤 Driver: {vehicle.driver_name}\n"

        if hasattr(vehicle, 'vehicle_type') and vehicle.vehicle_type:
            text += f"🏷️ Type: {vehicle.vehicle_type}\n"

        if hasattr(vehicle, 'year') and vehicle.year:
            text += f"📅 Year: {vehicle.year}\n"

        status = "✅ Active" if vehicle.active else "❌ Inactive"
        text += f"📊 Status: {status}\n"
        
        task_count = env['task.manager'].search_count([
            ('vehicle_id', '=', vehicle.id),
            ('state', 'in', ['draft', 'in_progress'])
        ])
        if task_count > 0:
            text += f"📋 Active Tasks: {task_count}\n"

        keyboard = [
            [{'text': '🏠 Main Menu', 'callback_data': 'menu'}],
            [{'text': '📋 My Tasks', 'callback_data': 'tasks'}]
        ]
        
        self._send_message(chat_id, text, keyboard)

    def _send_tasks(self, env, chat_id, user):
        """Send user tasks with enhanced debugging"""
        _logger.info(f"🔍 SEARCHING TASKS FOR USER:")
        _logger.info(f"   User: {user.name}")
        _logger.info(f"   User ID: {user.id}")
        _logger.info(f"   Telegram ID: {user.telegram_id}")
        _logger.info(f"   Is Admin: {user.is_admin}")
        
        tasks = env['task.manager'].search([
            ('telegram_user_id', '=', user.id),
            ('state', 'in', ['draft', 'in_progress'])
        ])
        
        _logger.info(f"   Found {len(tasks)} tasks")
        
        all_tasks = env['task.manager'].search([])
        _logger.info(f"   Total tasks in system: {len(all_tasks)}")
        
        for task in all_tasks:
            assigned_user = task.telegram_user_id.name if task.telegram_user_id else 'Unassigned'
            _logger.info(f"     Task: {task.title} → {assigned_user} (telegram_user_id: {task.telegram_user_id.id if task.telegram_user_id else 'None'})")
        
        if not tasks:
            text = "📋 Not active tasks!\n\n"
            text += f"🔍 **Debug info:**\n"
            text += f"User ID: {user.id}\n"
            text += f"Telegram ID: {user.telegram_id}\n"
            text += f"Total in system: {len(all_tasks)} tasks"

            keyboard = [[{'text': '🏠 Main Menu', 'callback_data': 'menu'}]]
            self._send_message(chat_id, text, keyboard)
            return
            
        text = "📋 **Your Tasks:**\n\n"
        keyboard = []
        
        for task in tasks:
            emoji = "🔄" if task.state == 'in_progress' else "📌"
            vehicle = f" ({task.vehicle_id.license_plate})" if task.vehicle_id else ""
            
            text += f"{emoji} **{task.title}**{vehicle}\n"
            if task.description:
                text += f"📝 {task.description}\n"
            text += "\n"
            
            vehicle_name = task.vehicle_id.name if task.vehicle_id else ''
            if vehicle_name:
                button_text = f'✅ Done: {vehicle_name} {task.title[:15]}...'
            else:
                button_text = f'✅ Done: {task.title[:15]}...'
            keyboard.append([{
                'text': button_text,
                'callback_data': f'done_{task.id}'
            }])
        
        # New button for completion date
        keyboard.append([{
            'text': '🗓️ Set Completion Date',
            'callback_data': f'set_day_{task.id}'
        }])
        keyboard.append([{'text': '🏠 Main Menu', 'callback_data': 'menu'}])
        self._send_message(chat_id, text, keyboard)

    def _mark_task_done(self, env, chat_id, task_id, user):
        """Mark task as done and return success status"""
        try:
            task = env['task.manager'].browse(task_id)
            
            if not task.exists():
                _logger.warning(f"❌ Task {task_id} not found")
                self._send_message(chat_id, "❌ Task not found.")
                return False
                
            if task.telegram_user_id != user:
                _logger.warning(f"❌ Task {task_id} not assigned to user {user.name}")
                self._send_message(chat_id, "❌ Task not assigned to you.")
                return False
            
            _logger.info(f"✅ Marking task '{task.title}' as done by {user.name}")
            
            task.with_context(from_telegram=True).action_complete()

            text = f"✅ **Task completed!**\n\n"
            text += f"📋 **{task.title}**\n"
            
            if task.description:
                text += f"📝 {task.description}\n"
                
            if task.vehicle_id:
                text += f"🚗 **Vehicle:** {task.vehicle_id.name}"
                if task.vehicle_id.license_plate:
                    text += f" ({task.vehicle_id.license_plate})"
                text += "\n"

            text += f"⏰ **Completed:** {fields.Datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            text += f"👤 **User:** {user.name}"

            keyboard = [
                [{'text': '📋 Other Tasks', 'callback_data': 'tasks'}],
                [{'text': '🏠 Main Menu', 'callback_data': 'menu'}]
            ]
            self._send_message(chat_id, text, keyboard)
            
            # Send notification to admin
            admin_text = f"🎉 **TASK COMPLETEDS!**\n\n"
            admin_text += f"👤 **User:** {user.name}\n"
            admin_text += f"📋 **Task:** {task.title}\n"

            if task.description:
                admin_text += f"📝 **Description:** {task.description}\n"

            if task.vehicle_id:
                admin_text += f"🚗 **Vehicle:** {task.vehicle_id.name}"
                if task.vehicle_id.license_plate:
                    admin_text += f" ({task.vehicle_id.license_plate})"
                admin_text += "\n"
                
            if task.priority:
                priority_emoji = {'low': '🟢', 'normal': '🟡', 'high': '🔴', 'urgent': '🚨'}.get(task.priority, '📌')
                admin_text += f"⚡ **Priority:** {priority_emoji} {dict(task._fields['priority'].selection).get(task.priority, task.priority)}\n"

            admin_text += f"⏰ **Completed:** {fields.Datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            admin_text += f"📊 **Status:** Completed"

            if self.admin_telegram_id:
                _logger.info(f"📤 Sending completion notification to admin {self.admin_telegram_id}")
                self._send_message(self.admin_telegram_id, admin_text)
                _logger.info(f"✅ Admin notification sent successfully")
            else:
                _logger.error(f"❌ No admin telegram ID configured!")
                
            return True
            
        except Exception as e:
            error_msg = f"❌ Error marking task {task_id} as done: {e}"
            _logger.error(error_msg)
            self._send_message(chat_id, "❌ Error marking task as completed.")
            return False

    def _send_report_prompt(self, env, chat_id):
        """Send report prompt"""
        text = "⚠️ **Report an issue**\n\nPlease describe the issue:"
        keyboard = [[{'text': '🏠 Main Menu', 'callback_data': 'menu'}]]
        self._send_message(chat_id, text, keyboard)

    def _handle_report(self, env, chat_id, user, text):
        """Handle user report with detailed logging"""
        _logger.info(f"📝 HANDLING REPORT:")
        _logger.info(f"   User: {user.name} (ID: {user.id})")
        _logger.info(f"   Chat ID: {chat_id}")
        _logger.info(f"   Text: '{text}'")
        _logger.info(f"   Is Admin: {user.is_admin}")
        
        if user.is_admin:
            _logger.info("👑 Skipping report creation for admin")
            return
            
        _logger.info("💾 Creating report in database...")
        report = env['task.report'].create({
            'name': f'Report from {user.name}',
            'description': text,
            'telegram_user_id': user.id,
            'state': 'new'
        })
        _logger.info(f"✅ Report created with ID: {report.id}")

        confirm_text = "✅ **Report sent!**\n\nThe administrator will review it."
        keyboard = [[{'text': '🏠 Main Menu', 'callback_data': 'menu'}]]
        _logger.info(f"📤 Sending confirmation to user...")
        self._send_message(chat_id, confirm_text, keyboard)
        _logger.info(f"✅ User confirmation sent")
        
        if self.admin_telegram_id:
            admin_text = f"⚠️ **New report!**\n👤 {user.name}\n📝 {text}"
            _logger.info(f"📤 Sending notification to admin {self.admin_telegram_id}...")
            self._send_message(self.admin_telegram_id, admin_text)
            _logger.info(f"✅ Admin notification sent")
        else:
            _logger.warning(f"⚠️ No admin telegram ID configured!")

    def _handle_photo_report(self, env, message, user):
        """Handle photo report"""
        chat_id = message['chat']['id']
        caption = message.get('caption', 'Photo report')
        photos = message['photo']
        
        largest_photo = max(photos, key=lambda p: p['file_size'])
        photo_url = self._get_file_url(largest_photo['file_id'])
        
        env['task.report'].create({
            'name': f'Photo Report from {user.name}',
            'description': caption,
            'telegram_user_id': user.id,
            'photo_urls': photo_url,
            'state': 'new'
        })

        confirm_text = "✅ **Photo report sent!**\n\nThe administrator will review it."
        keyboard = [[{'text': '🏠 Main Menu', 'callback_data': 'menu'}]]
        self._send_message(chat_id, confirm_text, keyboard)

        admin_text = f"📸 **New photo report!**\n👤 {user.name}\n📝 {caption}"
        self._send_message(self.admin_telegram_id, admin_text)
        
        self._forward_photo_to_admin(largest_photo['file_id'], admin_text)

    def _get_file_url(self, file_id):
        """Get file URL from Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getFile"
            response = requests.get(url, params={'file_id': file_id}, timeout=10)
            if response.ok:
                file_path = response.json()['result']['file_path']
                return f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        except Exception as e:
            _logger.error("Error getting file URL: %s", e)
        return None

    def _forward_photo_to_admin(self, file_id, caption):
        """Forward photo to admin"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            data = {
                'chat_id': self.admin_telegram_id,
                'photo': file_id,
                'caption': caption
            }
            requests.post(url, json=data, timeout=10)
        except Exception as e:
            _logger.error("Error forwarding photo: %s", e)

    def _send_message(self, chat_id, text, keyboard=None):
        """Send message to Telegram with enhanced logging"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        if keyboard:
            reply_markup = {'inline_keyboard': keyboard}
            data['reply_markup'] = json.dumps(reply_markup)
            
        try:
            _logger.info(f"📤 Sending message to {chat_id}: {text[:50]}...")
            response = requests.post(url, json=data, timeout=10)
            
            if response.ok:
                _logger.info(f"✅ Message sent successfully")
                return True
            else:
                error_data = response.json()
                error_desc = error_data.get('description', 'Unknown error')
                _logger.error(f"❌ Failed to send message: {error_desc}")
                return False
                
        except Exception as e:
            _logger.error(f"❌ Error sending message: {e}")
            return False

    def _answer_callback(self, callback_id, text="✅ OK", show_alert=False):
        """Answer callback query with proper feedback"""
        url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
        
        data = {
            'callback_query_id': callback_id,
            'text': text,
            'show_alert': show_alert
        }
        
        try:
            _logger.info(f"📤 Answering callback {callback_id} with: {text}")
            response = requests.post(url, json=data, timeout=10)
            
            if response.ok:
                _logger.info(f"✅ Callback answered successfully")
                return True
            else:
                _logger.error(f"❌ Failed to answer callback: {response.text}")
                return False
                
        except Exception as e:
            _logger.error(f"💥 Error answering callback: {e}")
            return False

    def send_task_notification(self, task):
        """Send detailed task notification to user"""
        if not task.telegram_user_id or not task.telegram_user_id.telegram_id:
            _logger.warning("❌ Cannot send task notification - no telegram user assigned")
            return
            
        if task.telegram_user_id.telegram_id == self.admin_telegram_id:
            _logger.info("ℹ️ Task assigned to admin - sending admin-specific notification instead")
            self._send_admin_task_notification(task)
            return
            
        _logger.info(f"📤 Sending task notification to USER: {task.telegram_user_id.name} (ID: {task.telegram_user_id.telegram_id})")

        text = f"📋 **New task!**\n\n"
        text += f"**{task.title}**\n"
        
        if task.description:
            text += f"📝 {task.description}\n\n"
        
        if task.vehicle_id:
            vehicle_info = f"🚗 **{task.vehicle_id.name}**"
            if task.vehicle_id.license_plate:
                vehicle_info += f" ({task.vehicle_id.license_plate})"
            if task.vehicle_id.driver_name:
                vehicle_info += f"\n👤 Driver: {task.vehicle_id.driver_name}"
            text += vehicle_info + "\n"
        
        priority_icons = {'0': '🔵', '1': '🟡', '2': '🟠', '3': '🔴'}
        priority_texts = {'0': 'Low', '1': 'Normal', '2': 'High', '3': 'Urgent'}
        priority_icon = priority_icons.get(task.priority, '🟡')
        priority_text = priority_texts.get(task.priority, 'Normal')
        text += f"{priority_icon} Priority: {priority_text}\n"

        state_icons = {'draft': '📝', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}
        state_texts = {'draft': 'Draft', 'in_progress': 'In Progress', 'completed': 'Completed', 'cancelled': 'Cancelled'}
        state_icon = state_icons.get(task.state, '📝')
        state_text = state_texts.get(task.state, 'Unknown')
        text += f"{state_icon} Status: {state_text}\n"
        
        if task.date_deadline:
            text += f"⏰ Deadline: {task.date_deadline.strftime('%d.%m.%Y %H:%M')}\n"

        if task.progress > 0:
            text += f"📊 Progress: {task.progress:.0f}%\n"
            
        keyboard = []
        
        if task.vehicle_id:
            keyboard.append([{
                'text': f'🚗 Info about {task.vehicle_id.name}',
                'callback_data': f'vehicle_info_{task.vehicle_id.id}'
            }])
        # Jauna poga izpildes dienai
        keyboard.append([{
            'text': '🗓️ Specify execution day',
            'callback_data': f'set_day_{task.id}'
        }])
        keyboard.extend([
            [{'text': '✅ Mark as done', 'callback_data': f'done_{task.id}'}],
            [{'text': '📋 All tasks', 'callback_data': 'tasks'}]
        ])
        
        self._send_message(task.telegram_user_id.telegram_id, text, keyboard)
        _logger.info(f"✅ Task notification sent to USER: {task.telegram_user_id.name}")
        
        if self.admin_telegram_id and task.telegram_user_id.telegram_id != self.admin_telegram_id:
            _logger.info(f"📤 Sending ADMIN notification about task assignment to: {task.telegram_user_id.name}")
            admin_text = f"📋 **New task assigned to employee!**\n\n"
            admin_text += f"👤 **Employee:** {task.telegram_user_id.name}\n"
            admin_text += f"📋 **Task:** {task.title}\n"

            if task.description:
                admin_text += f"📝 **Description:** {task.description}\n"

            if task.vehicle_id:
                admin_text += f"🚗 **Vehicle:** {task.vehicle_id.name}"
                if task.vehicle_id.license_plate:
                    admin_text += f" ({task.vehicle_id.license_plate})"
                admin_text += "\n"

            admin_text += f"{priority_icon} **Priority:** {priority_text}\n"
            admin_text += f"⏰ **Created:** {fields.Datetime.now().strftime('%d.%m.%Y %H:%M')}"

            self._send_message(self.admin_telegram_id, admin_text)
            _logger.info(f"✅ Admin notified about task assignment to: {task.telegram_user_id.name}")
        else:
            _logger.info(f"ℹ️ Skipping admin notification (task assigned to admin or no admin ID)")

    def _ask_for_execution_day(self, chat_id, task_id):
        """Send message asking for execution day"""
        text = f"🗓️ Please enter the day you can complete the task (e.g., '2025-08-15' or 'Friday')!"
        # ForceReply, lai Telegram klients parāda atbildes lauku
        reply_markup = json.dumps({"force_reply": True})
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'reply_markup': reply_markup
        }
        try:
            _logger.info(f"📤 Asking for execution day for task {task_id} to chat {chat_id}")
            response = requests.post(url, json=data, timeout=10)
            if response.ok:
                _logger.info(f"✅ Execution day request sent successfully")
            else:
                _logger.error(f"❌ Failed to send execution day request: {response.text}")
        except Exception as e:
            _logger.error(f"❌ Error sending execution day request: {e}")
