from odoo import models, fields

class TelegramUser(models.Model):
    _name = 'telegram.user'
    _description = 'Telegram User'
    _inherit = ['mail.thread']

    name = fields.Char('Name', required=True)
    telegram_id = fields.Char('Telegram ID', required=True)
    username = fields.Char('Username')
    is_admin = fields.Boolean('Is Admin', default=False)
    active = fields.Boolean('Active', default=True)
