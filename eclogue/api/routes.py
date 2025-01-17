from eclogue.api.menus import Menus
from eclogue.api.catheter import Catheter
from eclogue.api.auth import Auth
from eclogue.api.host import dump_inventory
import eclogue.api.inventory as cmdb
from eclogue.api.credential import credentials, add_credential, update_credential
from eclogue.api.console import run_task
import eclogue.api.team as team
import eclogue.api.notification as notification
import eclogue.api.log as log
import eclogue.api.configuration as configuration
import eclogue.api.task as task
import eclogue.api.book as book
import eclogue.api.playbook as playbook
import eclogue.api.app as application
import eclogue.api.job as job
import eclogue.api.dashboard as dashboard
import eclogue.api.setting as setting
import eclogue.api.user as user
import eclogue.api.key as keys
import eclogue.api.role as role

routes = [
    ('/login', Auth.login, ['POST']),
    ('/menus', Menus.get_menus, ['GET']),
    ('/menus', Menus.add_menu, ['POST']),
    ('/menus/<_id>', Menus.edit_menu, ['put']),
    ('/menus/<_id>', Menus.delete_menu, ['delete']),
    ('/playbook/dumper', Catheter.get, ['GET']),
    ('/playbook/dumper', Catheter.drop, ['DELETE']),
    ('/playbook/<_id>/rename', playbook.rename, ['PATCH']),
    ('/playbook/upload', playbook.upload, ['POST']),
    ('/playbook/folder', playbook.add_folder, ['POST']),
    ('/playbook/galaxy', playbook.import_galaxy, ['get']),
    ('/playbook/tags', playbook.get_tags, ['post']),
    ('/playbook/<_id>/file', playbook.edit_file, ['put']),
    ('/playbook/<_id>/file', playbook.remove_file, ['delete']),
    ('/playbook/edit/<_id>', playbook.get_file, ['GET']),
    ('/tasks', task.monitor, ['get']),
    ('/tasks/queue', task.get_queue_tasks, ['get']),
    ('/tasks/history', task.get_task_history, ['get']),
    ('/tasks/<_id>/logs', task.task_logs, ['get']),
    ('/tasks/<_id>/logs/buffer', task.task_log_buffer, ['get']),
    ('/tasks/<_id>/info', task.get_task_info, ['get']),
    ('/tasks/<_id>/retry', task.retry, ['post']),
    ('/tasks/<_id>/<state>/remove', task.delete_task, ['delete']),
    ('/tasks/<_id>/<state>/cancel', task.cancel, ['delete']),
    ('/tasks/<_id>/schedule', task.get_schedule_task, ['get']),
    ('/tasks/<_id>/rollback', task.rollback, ['post']),
    ('/tasks/<job_id>/schedule/pause', task.pause_schedule, ['put']),
    ('/tasks/<job_id>/schedule/resume', task.resume_schedule, ['put']),
    ('/tasks/<job_id>/schedule/remove', task.remove_schedule, ['delete']),
    ('/tasks/<job_id>/schedule/reschedule', task.reschedule_schedule, ['put']),
    ('/inventory/dumper', dump_inventory, ['GET', 'POST']),
    ('/books/all', book.all_books, ['GET']),
    ('/books', book.add_book, ['POST']),
    ('/books/<_id>', book.book_detail, ['get']),
    ('/books/<_id>', book.edit_book, ['put']),
    ('/books/<_id>', book.delete_book, ['delete']),
    ('/books', book.books, ['get']),
    ('/books/<_id>/playbook', book.get_playbook, ['GET']),
    ('/books/<_id>/download', book.download_book, ['GET']),
    ('/books/<_id>/playbook', book.upload_playbook, ['post']),
    ('/books/<_id>/entries', book.get_entry, ['GET']),
    ('/books/<name>/inventory', cmdb.get_inventory_by_book, ['GET']),
    ('/books/<_id>/roles', book.get_roles_by_book, ['GET']),
    ('/search/users', user.search_user, ['get']),
    ('/cmdb/inventory', cmdb.explore, ['post']),
    ('/cmdb/inventory', cmdb.get_inventory, ['get']),
    ('/cmdb/inventory/<_id>', cmdb.edit_inventory, ['put']),
    ('/cmdb/inventory/<_id>', cmdb.delete_inventory, ['delete']),
    ('/cmdb/devices', cmdb.get_devices, ['GET']),
    ('/cmdb/devices/<_id>', cmdb.get_device_info, ['GET']),
    ('/cmdb/devices/<_id>', cmdb.delete_inventory, ['delete']),
    ('/cmdb/regions', cmdb.regions, ['get']),
    ('/cmdb/regions', cmdb.add_region, ['post']),
    ('/cmdb/regions/<_id>', cmdb.update_region, ['put']),
    ('/cmdb/groups', cmdb.groups, ['get']),
    ('/cmdb/groups', cmdb.add_group, ['post']),
    ('/cmdb/groups/<_id>', cmdb.update_group, ['put']),
    ('/cmdb/groups/<_id>', cmdb.get_group_info, ['get']),
    ('/cmdb/groups/<_id>', cmdb.delete_group, ['delete']),
    ('/cmdb/groups/<_id>/hosts', cmdb.get_group_hosts, ['get']),
    ('/cmdb/hosts/<_id>', cmdb.get_node_info, ['get']),
    ('/cmdb/hosts', cmdb.get_inventory, ['get']),
    ('/cmdb/<user_id>/groups', cmdb.get_host_groups, ['get']),

    ('/jobs/preview/inventory', cmdb.preview_inventory, ['post']),
    ('/jobs', job.get_jobs, ['get']),
    ('/jobs', job.add_jobs, ['post']),
    ('/jobs/<_id>', job.get_job, ['get']),
    ('/jobs/<_id>', job.delete_job, ['delete']),
    ('/jobs/<_id>', job.check_job, ['post']),
    ('/jobs/<_id>/tasks', job.job_detail, ['get']),
    ('/jobs/runner/doc', job.runner_doc, ['get']),
    ('/jobs/runner/modules', job.runner_module, ['get']),
    ('/credentials', credentials, ['get']),
    ('/credentials', add_credential, ['post']),
    ('/credentials/<_id>', update_credential, ['put']),
    ('/apps', application.get_apps, ['get']),
    ('/apps', application.add_apps, ['post']),
    ('/apps/<_id>', application.update_app, ['put']),
    ('/configurations', configuration.list_config, ['get']),
    ('/configurations/<playbook_id>/register', configuration.get_register_config, ['get']),
    ('/configurations/<_id>', configuration.update_configuration, ['put']),
    ('/configurations/<_id>', configuration.get_config_info, ['get']),
    ('/configurations/<_id>', configuration.delete, ['delete']),
    ('/configurations', configuration.add_configuration, ['post']),
    ('/configurations/list/ids', configuration.get_configs_by_ids, ['get']),
    ('/execute', run_task, ['post']),
    ('/teams', team.add_team, ['post']),
    ('/teams', team.get_team_tree, ['get']),
    ('/teams/<_id>', team.get_team_info, ['get']),
    ('/teams/<_id>', team.update_team, ['put']),
    ('/teams/<_id>', team.delete_team, ['delete']),
    ('/teams/members', team.add_user_to_team, ['post']),
    ('/users', user.add_user, ['post']),
    ('/users/<_id>', user.get_user_info, ['get']),
    ('/users/<_id>', user.update_user, ['put']),
    ('/users/<_id>', user.delete_user, ['delete']),
    ('/users/<_id>', user.get_user_info, ['get']),
    ('/users/<_id>/profile', user.get_profile, ['get']),
    ('/users/<_id>/profile', user.save_profile, ['put']),
    ('/users/roles', user.get_current_roles, ['get']),
    ('/users/<user_id>/roles', user.bind_role, ['post']),
    ('/users/<user_id>/hosts', user.bind_hosts, ['post']),
    ('/users/email/send', user.send_verify_mail, ['post']),
    ('/users/email/verify', user.verify_mail, ['get']),
    ('/users/alert/notification', user.save_alert, ['post']),
    ('/users/password/reset', user.reset_pwd, ['put']),
    ('/sshkeys/public', keys.get_keys, ['get']),
    ('/sshkeys/public', keys.add_key, ['POST']),
    ('/roles', role.add_role, ['post']),
    ('/roles', role.get_roles, ['get']),
    ('/roles/<_id>', role.update_role, ['put']),
    ('/roles/<_id>/menus', role.get_role_menus, ['get']),
    ('/notifications', notification.get_notify, ['get']),
    ('/notifications/read', notification.mark_read, ['put']),
    # ('/docker', docker.test_docker, ['get']),
    ('/webhooks/job', job.job_webhook, ['post']),
    ('/logs', log.log_query, ['get']),
    ('/test', setting.test, ['get']),
    ('/dashboard', dashboard.dashboard, ['get']),
    ('/setting', setting.add_setting, ['post']),
    ('/setting', setting.get_setting, ['get']),
]
