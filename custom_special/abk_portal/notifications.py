import frappe
from frappe.utils import nowdate


def notify_system_managers(subject, message, document_type=None, document_name=None):
	"""Notify enabled System Manager users without blocking the source transaction."""
	try:
		users = get_system_manager_users()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Failed to find System Managers for ABK Portal notification",
		)
		return

	for user in users:
		try:
			notification = _create_notification_log(user, subject, message, document_type, document_name)
			_create_todo(user, message, document_type, document_name)
			if notification:
				_publish_realtime_notification(
					user,
					subject,
					message,
					document_type,
					document_name,
					notification.name,
				)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				"Failed to notify System Managers for ABK Portal activity",
			)


def get_system_manager_users():
	users = frappe.get_all(
		"Has Role",
		filters={"role": "System Manager", "parenttype": "User"},
		pluck="parent",
		group_by="parent",
	)
	users = sorted({user for user in users if user and user != "Guest"})
	if not users:
		return []

	return frappe.get_all(
		"User",
		filters={
			"name": ["in", users],
			"enabled": 1,
			"user_type": "System User",
		},
		pluck="name",
	)


def _create_notification_log(user, subject, message, document_type=None, document_name=None):
	filters = {
		"for_user": user,
		"type": "Alert",
		"subject": subject,
		"read": 0,
	}
	if document_type and document_name:
		filters.update({"document_type": document_type, "document_name": document_name})

	if frappe.db.exists("Notification Log", filters):
		return

	data = {
		"doctype": "Notification Log",
		"subject": subject,
		"email_content": message,
		"for_user": user,
		"type": "Alert",
		"from_user": _notification_sender(),
		"read": 0,
	}
	if document_type and document_name:
		data.update(
			{
				"document_type": document_type,
				"document_name": document_name,
			}
		)

	return frappe.get_doc(data).insert(ignore_permissions=True)


def _create_todo(user, message, document_type=None, document_name=None):
	if document_type and document_name:
		if frappe.db.exists(
			"ToDo",
			{
				"allocated_to": user,
				"reference_type": document_type,
				"reference_name": document_name,
				"status": "Open",
			},
		):
			return

	todo = frappe.new_doc("ToDo")
	todo.allocated_to = user
	todo.assigned_by = _notification_sender()
	todo.description = message
	todo.date = nowdate()
	todo.priority = "Medium"
	todo.status = "Open"
	if document_type and document_name:
		todo.reference_type = document_type
		todo.reference_name = document_name
	todo.insert(ignore_permissions=True)


def _notification_sender():
	if frappe.session.user and frappe.session.user != "Guest":
		return frappe.session.user
	return "Administrator"


def _publish_realtime_notification(
	user,
	subject,
	message,
	document_type=None,
	document_name=None,
	notification_log_name=None,
):
	payload = {
		"subject": subject,
		"message": message,
		"document_type": document_type,
		"document_name": document_name,
		"notification_log": notification_log_name,
	}
	frappe.publish_realtime(event="msgprint", message=payload, user=user)
	frappe.publish_realtime(event="abk_admin_notification", message=payload, user=user)


@frappe.whitelist()
def get_unread_abk_notification_count():
	if frappe.session.user == "Guest" or not _can_use_abk_desk_notifications():
		return 0

	return frappe.db.count(
		"Notification Log",
		{
			"for_user": frappe.session.user,
			"read": 0,
			"type": "Alert",
		},
	)


def _can_use_abk_desk_notifications():
	return bool({"System Manager", "ABK Admin"}.intersection(set(frappe.get_roles())))
