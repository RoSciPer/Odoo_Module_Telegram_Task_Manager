# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class TaskManager(models.Model):
    """Main task management model"""
    _name = 'task.manager'
    _description = 'Task Manager'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'
    _rec_name = 'title'

    # Basic fields
    title = fields.Char(string='Title', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    
    # Status and priority
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1', tracking=True)
    
    # Assignments
    assigned_user_id = fields.Many2one(
        'res.users', 
        string='Assigned User', 
        tracking=True,
        help="User responsible for this task"
    )
    telegram_user_id = fields.Many2one(
        'telegram.user',
        string='Telegram User',
        help="Telegram user assigned to this task"
    )
    
    # Vehicle relation
    vehicle_id = fields.Many2one(
        'task.vehicle',
        string='Vehicle',
        help="Vehicle associated with this task"
    )
    
    # Dates
    date_deadline = fields.Datetime(string='Deadline', tracking=True)
    date_start = fields.Datetime(string='Start Date', tracking=True)
    date_completed = fields.Datetime(string='Completed Date', readonly=True)
    
    # Progress
    progress = fields.Float(string='Progress (%)', default=0.0, tracking=True)
    estimated_hours = fields.Float(string='Estimated Hours')
    actual_hours = fields.Float(string='Actual Hours')
    
    # Tags and categorization
    tag_ids = fields.Many2many(
        'task.tag',
        string='Tags',
        help="Tags for categorizing tasks"
    )
    category_id = fields.Many2one(
        'task.category',
        string='Category',
        help="Task category"
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    # Telegram integration
    telegram_message_sent = fields.Boolean(string='Telegram Notification Sent', default=False)
    telegram_chat_id = fields.Char(string='Telegram Chat ID')
    
    # Comments and notes
    comment_ids = fields.One2many(
        'task.comment',
        'task_id',
        string='Comments'
    )
    internal_notes = fields.Text(string='Internal Notes')
    
    # Computed fields
    is_overdue = fields.Boolean(string='Is Overdue', compute='_compute_is_overdue', store=True)
    days_to_deadline = fields.Integer(string='Days to Deadline', compute='_compute_days_to_deadline')
    
    # Colors for kanban view
    color = fields.Integer(string='Color Index', default=0)
    
    @api.depends('date_deadline', 'state')
    def _compute_is_overdue(self):
        """Compute if task is overdue"""
        now = fields.Datetime.now()
        for task in self:
            task.is_overdue = (
                task.date_deadline and 
                task.date_deadline < now and 
                task.state not in ['completed', 'cancelled']
            )
    
    @api.depends('date_deadline')
    def _compute_days_to_deadline(self):
        """Compute days remaining to deadline"""
        now = fields.Datetime.now()
        for task in self:
            if task.date_deadline:
                delta = task.date_deadline - now
                task.days_to_deadline = delta.days
            else:
                task.days_to_deadline = 0
    
    @api.model
    def create(self, vals):
        """Override create to send Telegram notification"""
        task = super(TaskManager, self).create(vals)
        if task.telegram_user_id and task.telegram_user_id.telegram_id:
            task._send_telegram_notification('created')
        return task
    
    def write(self, vals):
        """Override write to send Telegram notifications on changes"""
        # PREVENT LOOPS: Skip notification if from telegram or specific contexts
        if ('telegram_message_sent' in vals or 
            self.env.context.get('from_telegram') or 
            self.env.context.get('skip_telegram_notification')):
            return super(TaskManager, self).write(vals)
            
        result = super(TaskManager, self).write(vals)
        
        # Send notification only on state change AND not from action methods
        if ('state' in vals and 
            not self.env.context.get('from_action_method') and
            not self.env.context.get('from_telegram')):
            for task in self:
                if task.telegram_user_id and task.telegram_user_id.telegram_id:
                    task._send_telegram_notification('updated')
        
        # Update completion date (with context to prevent loops)
        if 'state' in vals and vals['state'] == 'completed':
            # Use sudo with context to avoid triggering notification again
            self.sudo().with_context(skip_telegram_notification=True).write({
                'date_completed': fields.Datetime.now()
            })
            
        return result
    
    def action_start(self):
        """Start the task"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft tasks can be started.'))
        # Use context to prevent duplicate notifications
        self.with_context(from_action_method=True).write({
            'state': 'in_progress',
            'date_start': fields.Datetime.now()
        })
        self._send_telegram_notification('started')
        return True
    
    def action_complete(self):
        """Complete the task"""
        self.ensure_one()
        if self.state not in ['draft', 'in_progress']:
            raise UserError(_('Only draft or in-progress tasks can be completed.'))
        # Use context to prevent duplicate notifications
        self.with_context(from_action_method=True).write({
            'state': 'completed',
            'date_completed': fields.Datetime.now(),
            'progress': 100.0
        })
        self._send_telegram_notification('completed')
        return True
    
    def action_cancel(self):
        """Cancel the task"""
        self.ensure_one()
        if self.state == 'completed':
            raise UserError(_('Completed tasks cannot be cancelled.'))
        # Use context to prevent duplicate notifications  
        self.with_context(from_action_method=True).write({
            'state': 'cancelled',
            'date_cancelled': fields.Datetime.now()
        })
        self._send_telegram_notification('cancelled')
        return True
    
    def action_reset_to_draft(self):
        """Reset task to draft"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'date_start': False,
            'date_completed': False,
            'progress': 0.0
        })
        return True
    
    def _send_telegram_notification(self, action):
        """Send Telegram notification"""
        try:
            # Get active telegram configuration
            telegram_config = self.env['telegram.config'].search([('active', '=', True)], limit=1)
            if not telegram_config or not telegram_config.bot_token:
                _logger.warning("No active Telegram configuration found")
                return False
            
            # Check if task has telegram user assigned
            if self.telegram_user_id and self.telegram_user_id.telegram_id:
                telegram_user = self.telegram_user_id
                
                # Find running telegram service
                telegram_service = self.env['telegram.service'].search([
                    ('bot_token', '=', telegram_config.bot_token),
                    ('is_running', '=', True)
                ], limit=1)
                
                if telegram_service:
                    # Use proper notification method with buttons
                    telegram_service.send_task_notification(self)
                    self.telegram_message_sent = True
                    _logger.info("Telegram notification sent to %s", telegram_user.name)
                else:
                    _logger.warning("No running Telegram service found")
            else:
                _logger.warning("No telegram user assigned to task: %s", self.title)
            
        except Exception as e:
            _logger.error(f"Error sending Telegram notification: {str(e)}")
            return False
    
    
    @api.constrains('progress')
    def _check_progress(self):
        """Validate progress value"""
        for task in self:
            if task.progress < 0 or task.progress > 100:
                raise ValidationError(_('Progress must be between 0 and 100.'))
    
    @api.constrains('date_deadline', 'date_start')
    def _check_dates(self):
        """Validate dates"""
        for task in self:
            if task.date_deadline and task.date_start:
                if task.date_deadline < task.date_start:
                    raise ValidationError(_('Deadline cannot be earlier than start date.'))

    def action_view_comments(self):
        """Action to view task comments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task Comments'),
            'res_model': 'task.comment',
            'view_mode': 'list,form',
            'domain': [('task_id', '=', self.id)],
            'context': {'default_task_id': self.id}
        }


class TaskCategory(models.Model):
    """Task categories"""
    _name = 'task.category'
    _description = 'Task Category'
    _order = 'sequence, name'
    
    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    color = fields.Integer(string='Color Index', default=0)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count')
    
    def _compute_task_count(self):
        """Compute number of tasks in this category"""
        for category in self:
            category.task_count = self.env['task.manager'].search_count([
                ('category_id', '=', category.id)
            ])


class TaskTag(models.Model):
    """Task tags"""
    _name = 'task.tag'
    _description = 'Task Tag'
    _order = 'name'
    
    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)
    
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count')
    
    def _compute_task_count(self):
        """Compute number of tasks with this tag"""
        for tag in self:
            tag.task_count = self.env['task.manager'].search_count([
                ('tag_ids', 'in', tag.id)
            ])


class TaskComment(models.Model):
    """Task comments"""
    _name = 'task.comment'
    _description = 'Task Comment'
    _order = 'create_date desc'
    _rec_name = 'comment'
    
    task_id = fields.Many2one('task.manager', string='Task', required=True, ondelete='cascade')
    comment = fields.Text(string='Comment', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    is_internal = fields.Boolean(string='Internal Comment', default=False)
    telegram_user_id = fields.Many2one('telegram.user', string='Telegram User')
    
    def name_get(self):
        """Custom name_get for comments"""
        result = []
        for comment in self:
            name = comment.comment[:50]
            if len(comment.comment) > 50:
                name += "..."
            result.append((comment.id, name))
        return result
    
    @api.model
    def get_dashboard_data(self):
        """Get dashboard statistics"""
        data = {}
        
        # Task statistics
        all_tasks = self.search([])
        data['total_tasks'] = len(all_tasks)
        data['completed_tasks'] = len(all_tasks.filtered(lambda t: t.state == 'completed'))
        data['in_progress_tasks'] = len(all_tasks.filtered(lambda t: t.state == 'in_progress'))
        data['overdue_tasks'] = len(all_tasks.filtered(lambda t: t.is_overdue))
        
        # User statistics
        telegram_users = self.env['telegram.user'].search([('is_active', '=', True)])
        data['telegram_users'] = len(telegram_users)
        
        # Vehicle statistics
        vehicles = self.env['task.vehicle'].search([('active', '=', True)])
        data['vehicles'] = len(vehicles)
        vehicle_alerts = vehicles.filtered(lambda v: v.insurance_alert or v.inspection_alert or v.service_alert)
        data['vehicle_alerts'] = len(vehicle_alerts)
        
        # Telegram statistics
        config = self.env['telegram.config'].search([('is_active', '=', True)], limit=1)
        data['messages_today'] = config.messages_sent_today if config else 0
        
        return data
