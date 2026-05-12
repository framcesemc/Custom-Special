import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

from custom_special.abk_portal.notifications import notify_system_managers


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
		notify_system_managers(
			"Member baru menunggu verifikasi",
			"Ada member ABK baru yang perlu diverifikasi.",
			self.doctype,
			self.name,
		)


def has_abk_admin_role():
	return frappe.session.user == "Administrator" or bool(ADMIN_ROLES.intersection(set(frappe.get_roles())))


def require_abk_admin_role():
	if not has_abk_admin_role():
		frappe.throw(_("Only ABK Admin or System Manager can perform this action."), frappe.PermissionError)


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
