from odoo import models, fields

class TaskVehicle(models.Model):
    _name = 'task.vehicle'
    _description = 'Task Vehicle'
    _inherit = ['mail.thread']

    name = fields.Char('Vehicle Name', required=True)
    license_plate = fields.Char('License Plate')
    driver_name = fields.Char('Driver Name')
    active = fields.Boolean('Active', default=True)
