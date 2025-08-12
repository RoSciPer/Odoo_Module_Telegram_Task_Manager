# Telegram Task Manager 2

Telegram Task Manager 2 is an Odoo module for managing tasks with Telegram bot integration. Originally developed for car dealership and vehicle logistics, but easily adaptable for any business task management scenario. Users can receive, complete, and comment on tasks directly from Telegram. Includes vehicle management, user management, and reporting features.

## Features
- Telegram bot integration for task notifications and actions
- Assign tasks to users and vehicles
- Inline buttons for task actions (complete, info, set execution day)
- User and vehicle management
- Reporting and photo reports

## Installation
1. Copy the module folder `telegram_task_manager_2` to your Odoo `addons` directory.
2. Install required Python packages (see `requirements.txt`).
3. Update Odoo app list and install the module via Odoo interface.

## Configuration
- Set up your Telegram bot and obtain the bot token.
- Configure the bot token and admin Telegram ID in the module settings.
- Set up webhook URL for Telegram bot to point to your server.

## Usage
- Users receive task notifications in Telegram.
- Inline buttons allow users to mark tasks as done, view vehicle info, or set execution day.
- Admin receives notifications about new users, reports, and completed tasks.

## License
AGPL-3

## Author
Rosciper
