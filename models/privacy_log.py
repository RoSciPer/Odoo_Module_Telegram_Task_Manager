# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PrivacyLog(models.Model):
    """Privacy Log model for tracking sensitive actions"""
    _name = 'privacy.log'
    _description = 'Privacy Log'
    _order = 'create_date desc'

    name = fields.Char(string='Action', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    description = fields.Text(string='Description')
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now(), required=True)
