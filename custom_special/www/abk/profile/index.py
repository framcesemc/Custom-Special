import frappe
from custom_special.abk_portal.api import get_current_member_profile, get_current_member_status


def get_context(context):
	context.no_cache = 1
	context.title = "Profil Member"

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/abk/login?redirect-to=/abk/profile"
		raise frappe.Redirect

	context.member_status = get_current_member_status()
	profile = get_current_member_profile()

	if profile:
		context.profile = profile
		context.user_image = frappe.db.get_value("User", frappe.session.user, "user_image") or ""
	else:
		context.profile = None
		context.user_image = ""

	context.user_email = frappe.session.user
	context.user_full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]
