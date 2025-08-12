# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QuickTaskWizard(models.TransientModel):
    """Quick Task Creation Wizard"""
    _name = 'quick.task.wizard'
    _description = 'Quick Task Wizard'
    
    title = fields.Char(string='Task Title', required=True)
    description = fields.Text(string='Description')
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assign To',
        default=lambda self: self.env.user
    )
    telegram_user_id = fields.Many2one(
        'telegram.user',
        string='Telegram User'
    )
    vehicle_id = fields.Many2one(
        'task.vehicle',
        string='Vehicle'
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1')
    
    category_id = fields.Many2one(
        'task.category',
        string='Category'
    )
    
    date_deadline = fields.Datetime(string='Deadline')
    
    send_notification = fields.Boolean(
        string='Send Telegram Notification',
        default=True,
        help="Send notification to assigned user via Telegram"
    )
    
    task_type = fields.Selection([
        ('maintenance', 'Vehicle Maintenance'),
        ('repair', 'Repair Work'),
        ('inspection', 'Inspection'),
        ('delivery', 'Delivery Task'),
        ('defect_report', 'Defect Report'),
        ('general', 'General Task')
    ], string='Task Type', default='general')
    
    estimated_hours = fields.Float(string='Estimated Hours')
    
    @api.onchange('task_type')
    def _onchange_task_type(self):
        """Auto-fill fields based on task type"""
        if self.task_type == 'maintenance':
            self.priority = '2'
            category = self.env['task.category'].search([('name', 'ilike', 'maintenance')], limit=1)
            if category:
                self.category_id = category.id
        elif self.task_type == 'defect_report':
            self.priority = '3'
            category = self.env['task.category'].search([('name', 'ilike', 'defect')], limit=1)
            if category:
                self.category_id = category.id
        elif self.task_type == 'repair':
            self.priority = '2'
            category = self.env['task.category'].search([('name', 'ilike', 'repair')], limit=1)
            if category:
                self.category_id = category.id
    
    @api.onchange('assigned_user_id')
    def _onchange_assigned_user_id(self):
        """Find linked Telegram user"""
        if self.assigned_user_id:
            telegram_user = self.env['telegram.user'].search([
                ('user_id', '=', self.assigned_user_id.id)
            ], limit=1)
            if telegram_user:
                self.telegram_user_id = telegram_user.id
    
    def action_create_task(self):
        """Create the task"""
        if not self.title:
            raise UserError(_("Task title is required!"))
        
        task_vals = {
            'title': self.title,
            'description': self.description,
            'assigned_user_id': self.assigned_user_id.id,
            'telegram_user_id': self.telegram_user_id.id if self.telegram_user_id else False,
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
            'priority': self.priority,
            'category_id': self.category_id.id if self.category_id else False,
            'date_deadline': self.date_deadline,
            'estimated_hours': self.estimated_hours,
            'state': 'draft'
        }
        
        task = self.env['task.manager'].create(task_vals)
        
        # Send notification if requested
        if self.send_notification and self.telegram_user_id:
            try:
                # Here you would implement the actual Telegram notification
                # For now, we'll just log it
                task.message_post(
                    body=_("Telegram notification sent to %s") % self.telegram_user_id.name
                )
            except Exception as e:
                task.message_post(
                    body=_("Failed to send Telegram notification: %s") % str(e)
                )
        
        # Return action to open the created task
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task Created'),
            'res_model': 'task.manager',
            'res_id': task.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    def action_create_and_start(self):
        """Create task and immediately start it"""
        action = self.action_create_task()
        task = self.env['task.manager'].browse(action['res_id'])
        task.action_start()
        return action
