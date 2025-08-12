# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TaskReport(models.Model):
    _name = 'task.report'
    _description = 'Task Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Report Title', required=True)
    description = fields.Text('Description', required=True)
    telegram_user_id = fields.Many2one('telegram.user', string='Reporter', required=True)
    state = fields.Selection([
        ('new', 'New'),
        ('in_review', 'In Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], default='new', string='Status', tracking=True)
    
    photo_urls = fields.Text('Photo URLs')  # Store Telegram photo URLs
    admin_response = fields.Text('Admin Response')
    create_date = fields.Datetime('Created', default=fields.Datetime.now)
    
    def action_resolve(self):
        self.state = 'resolved'
        
    def action_close(self):
        self.state = 'closed'
