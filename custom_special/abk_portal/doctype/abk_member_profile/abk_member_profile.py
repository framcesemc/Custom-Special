import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html, now, nowdate


ADMIN_ROLES = {"ABK Admin", "System Manager"}


class ABKMemberProfile(Document):
	def before_insert(self):
		if not self.verification_status:
			self.verification_status = "Pending"
		if self.user:
			self.owner = self.user

	def validate(self):
		if self.is_new() and not has_abk_admin_role():
			self.verification_status = "Pending"
			self.verified_by = None
			self.verified_on = None

	def after_insert(self):
		notify_abk_admins(self)


def has_abk_admin_role():
	return frappe.session.user == "Administrator" or bool(ADMIN_ROLES.intersection(set(frappe.get_roles())))


def require_abk_admin_role():
	if not has_abk_admin_role():
		frappe.throw(_("Only ABK Admin or System Manager can perform this action."), frappe.PermissionError)


def notify_abk_admins(profile):
	message = _("Member ABK baru menunggu verifikasi: {0}").format(profile.full_name)
	desk_link = f"/app/abk-member-profile/{profile.name}"
	description = f'{escape_html(message)}<br><a href="{desk_link}">{desk_link}</a>'
	admin_users = get_abk_admin_users()

	for user in admin_users:
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": user,
				"assigned_by": frappe.session.user if frappe.session.user != "Guest" else "Administrator",
				"description": description,
				"reference_type": "ABK Member Profile",
				"reference_name": profile.name,
				"date": nowdate(),
				"priority": "Medium",
				"status": "Open",
			}
		).insert(ignore_permissions=True)


def get_abk_admin_users():
	rows = frappe.get_all(
		"Has Role",
		filters={"role": "ABK Admin", "parenttype": "User"},
		fields=["parent"],
		group_by="parent",
	)
	users = []
	for row in rows:
		user = row.parent
		if frappe.db.get_value("User", user, "enabled"):
			users.append(user)

	return users


@frappe.whitelist()
def verify_member(name):
	require_abk_admin_role()
	profile = frappe.get_doc("ABK Member Profile", name)
	profile.db_set(
		{
			"verification_status": "Verified",
			"verified_by": frappe.session.user,
			"verified_on": now(),
		}
	)
	return {"name": profile.name}


@frappe.whitelist()
def reject_member(name):
	require_abk_admin_role()
	profile = frappe.get_doc("ABK Member Profile", name)
	profile.db_set(
		{
			"verification_status": "Rejected",
			"verified_by": frappe.session.user,
			"verified_on": now(),
		}
	)
	return {"name": profile.name}
