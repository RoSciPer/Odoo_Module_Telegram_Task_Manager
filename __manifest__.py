# -*- coding: utf-8 -*-
{
    'name': 'Telegram Task Manager',
    'version': '2.0.0',
    'category': 'Productivity',
    'summary': 'Task management with Telegram bot integration',
    'license': 'AGPL-3',
    'description': """
        Simple task manager with Telegram bot integration.
        Features:
        - Telegram bot configuration
        - User management
        - Vehicle management  
        - Task management
        - Reports from users
    """,
    'author': 'Rosciper',
    'depends': ['base', 'mail'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/telegram_config_views.xml',
        'views/telegram_user_views.xml',
        'views/vehicle_views.xml',
        'views/task_manager_views.xml',
        'views/telegram_bot_views.xml',
        'wizard/quick_task_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    
}
