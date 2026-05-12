import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

from custom_special.abk_portal.notifications import notify_system_managers


ADMIN_ROLES = {"ABK Admin", "System Manager"}


class ABKPlaceExperience(Document):
	def before_insert(self):
		self.set_defaults()

	def validate(self):
		self.validate_badges()

	def after_insert(self):
		notify_system_managers(
			"Pengalaman baru menunggu review",
			"Ada pengalaman parent baru yang perlu dicek admin.",
			self.doctype,
			self.name,
		)

	def set_defaults(self):
		if not self.verification_status:
			self.verification_status = "New"
		if not self.reviewer_user and frappe.session.user != "Guest":
			self.reviewer_user = frappe.session.user

	def validate_badges(self):
		seen = set()
		for row in self.get("badges") or []:
			if row.badge in seen:
				frappe.throw(_("Badge {0} dipilih lebih dari satu kali.").format(row.badge))
			seen.add(row.badge)

			if not frappe.db.exists("ABK Experience Badge", {"name": row.badge, "published": 1}):
				frappe.throw(_("Badge tidak valid atau belum dipublikasikan."))


def has_abk_admin_role():
	return bool(ADMIN_ROLES.intersection(set(frappe.get_roles())))


def require_abk_admin_role():
	if not has_abk_admin_role():
		frappe.throw(_("Only ABK Admin or System Manager can perform this action."), frappe.PermissionError)


@frappe.whitelist()
def approve_experience(name):
	require_abk_admin_role()
	experience = frappe.get_doc("ABK Place Experience", name)
	experience.db_set(
		{
			"verification_status": "Approved",
			"published": 1,
			"reviewed_by": frappe.session.user,
			"reviewed_on": now(),
		}
	)
	return {"name": experience.name, "published": 1}


@frappe.whitelist()
def reject_experience(name):
	require_abk_admin_role()
	experience = frappe.get_doc("ABK Place Experience", name)
	experience.db_set(
		{
			"verification_status": "Rejected",
			"published": 0,
			"reviewed_by": frappe.session.user,
			"reviewed_on": now(),
		}
	)
	return {"name": experience.name, "published": 0}
