# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Task(models.Model):
    _name = 'task.task'
    _description = 'Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char('Task Name', required=True, tracking=True)
    description = fields.Text('Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], default='draft', tracking=True)
    
    # Relations
    user_id = fields.Many2one('telegram.user', string='Assigned User', tracking=True)
    vehicle_id = fields.Many2one('task.vehicle', string='Vehicle', tracking=True)
    
    # Dates
    create_date = fields.Datetime('Created', default=lambda self: fields.Datetime.now())
    deadline = fields.Datetime('Deadline', tracking=True)
    
    @api.model
    def create(self, vals):
        """Override create to send notification"""
        task = super().create(vals)
        if task.user_id and task.user_id.telegram_id:
            self._send_task_notification(task)
        return task
    
    def write(self, vals):
        """Override write to send notifications on assignment"""
        result = super().write(vals)
        if 'user_id' in vals:
            for task in self:
                if task.user_id and task.user_id.telegram_id:
                    self._send_task_notification(task)
        return result
    
    def _send_task_notification(self, task):
        """Send task notification via Telegram"""
        service = self.env['telegram.service'].search([('is_running', '=', True)], limit=1)
        if service:
            service.send_task_notification(task)
    
    def action_start(self):
        self.state = 'in_progress'
        
    def action_done(self):
        self.state = 'done'
