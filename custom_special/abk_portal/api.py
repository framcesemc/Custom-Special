import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cstr, strip_html, validate_email_address, validate_phone_number


RELATIONSHIP_OPTIONS = {"Parent", "Guardian", "Teacher", "Therapist", "School Staff", "Other"}
DESK_ROLES = {"System Manager", "ABK Admin"}
FRONTEND_ONLY_ROLES = {"Website User"}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=60 * 60)
def register_abk_member(full_name, email, phone, password, relationship, city=None, district=None):
	full_name = strip_html(cstr(full_name)).strip()
	email = cstr(email).strip().lower()
	phone = strip_html(cstr(phone)).strip()
	relationship = cstr(relationship).strip()
	city = strip_html(cstr(city)).strip()
	district = strip_html(cstr(district)).strip()

	if not full_name or not email or not phone or not password or not relationship:
		frappe.throw(_("Name, email, phone, password, and relationship are required."))

	email = validate_email_address(email, throw=True)
	if not validate_phone_number(phone):
		frappe.throw(_("Please enter a valid phone number."))
	if relationship not in RELATIONSHIP_OPTIONS:
		frappe.throw(_("Please choose a valid relationship."))
	if frappe.db.exists("User", email):
		frappe.throw(_("Email ini sudah terdaftar. Silakan login atau gunakan email lain."))

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name,
			"full_name": full_name,
			"enabled": 1,
			"user_type": "Website User",
			"new_password": password,
			"send_welcome_email": 0,
		}
	)
	user.append("roles", {"role": "Website User"})
	user.insert(ignore_permissions=True)

	profile = frappe.get_doc(
		{
			"doctype": "ABK Member Profile",
			"user": user.name,
			"full_name": full_name,
			"phone": phone,
			"email": email,
			"relationship": relationship,
			"city": city,
			"district": district,
			"verification_status": "Pending",
		}
	)
	profile.owner = user.name
	profile.insert(ignore_permissions=True)

	return {
		"ok": True,
		"message": _("Registrasi berhasil. Akun Anda menunggu verifikasi admin."),
	}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60 * 60)
def complete_abk_member_profile(full_name, phone, relationship, city=None, district=None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login first."))

	if frappe.db.exists("ABK Member Profile", {"user": frappe.session.user}):
		frappe.throw(_("Profil member ABK sudah ada untuk akun ini."))

	full_name = strip_html(cstr(full_name)).strip()
	phone = strip_html(cstr(phone)).strip()
	relationship = cstr(relationship).strip()
	city = strip_html(cstr(city)).strip()
	district = strip_html(cstr(district)).strip()
	email = frappe.db.get_value("User", frappe.session.user, "email") or frappe.session.user

	if not full_name or not phone or not relationship:
		frappe.throw(_("Name, phone, and relationship are required."))
	if not validate_phone_number(phone):
		frappe.throw(_("Please enter a valid phone number."))
	if relationship not in RELATIONSHIP_OPTIONS:
		frappe.throw(_("Please choose a valid relationship."))

	profile = frappe.get_doc(
		{
			"doctype": "ABK Member Profile",
			"user": frappe.session.user,
			"full_name": full_name,
			"phone": phone,
			"email": email,
			"relationship": relationship,
			"city": city,
			"district": district,
			"verification_status": "Pending",
		}
	)
	profile.owner = frappe.session.user
	profile.insert(ignore_permissions=True)

	return {
		"ok": True,
		"message": _("Registrasi berhasil. Akun Anda menunggu verifikasi admin."),
	}


def get_current_member_profile():
	if frappe.session.user == "Guest":
		return None

	name = frappe.db.get_value("ABK Member Profile", {"user": frappe.session.user}, "name")
	if not name:
		return None

	return frappe.get_doc("ABK Member Profile", name)


def get_current_member_status():
	if frappe.session.user == "Guest":
		return "guest"

	if is_desk_user_allowed():
		return "verified"

	status = frappe.db.get_value(
		"ABK Member Profile",
		{"user": frappe.session.user},
		"verification_status",
	)
	return status.lower() if status else "missing"


def require_verified_member():
	status = get_current_member_status()
	if status != "verified":
		if status == "pending":
			message = _("Akun Anda sedang menunggu verifikasi admin.")
		elif status == "rejected":
			message = _("Akun Anda belum dapat mengirim info. Hubungi admin.")
		elif status == "missing":
			message = _("Silakan lengkapi registrasi member ABK terlebih dahulu.")
		else:
			message = _("Please login to submit information.")

		frappe.throw(message, frappe.PermissionError)


def redirect_members_from_desk():
	if not hasattr(frappe.local, "request"):
		return

	path = frappe.local.request.path or ""
	if not is_desk_route(path):
		return

	if frappe.session.user == "Guest":
		return

	if is_abk_admin_user(frappe.session.user):
		return

	if not is_frontend_only_user(frappe.session.user):
		return

	frappe.local.flags.redirect_location = "/abk"
	raise frappe.Redirect


def is_desk_user_allowed():
	return is_abk_admin_user(frappe.session.user)


def is_abk_admin_user(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	return bool(DESK_ROLES.intersection(roles))


def is_frontend_only_user(user=None):
	user = user or frappe.session.user
	if user in ("Guest", "Administrator"):
		return False

	roles = set(frappe.get_roles(user))
	return bool(roles.intersection(FRONTEND_ONLY_ROLES)) and not bool(roles.intersection(DESK_ROLES))


def is_desk_route(path):
	return path == "/app" or path.startswith("/app/") or path == "/desk" or path.startswith("/desk/")


def get_website_user_home_page(user):
	if is_frontend_only_user(user):
		return "abk"

	return None
