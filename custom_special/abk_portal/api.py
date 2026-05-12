import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cstr, getdate, strip_html, validate_email_address, validate_phone_number


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


@frappe.whitelist()
def get_member_login_result():
	"""Return ABK member login result and logout unverified frontend users."""
	if frappe.session.user == "Guest":
		return {
			"status": "guest",
			"verified": False,
			"logged_out": True,
			"redirect_to": "/abk/login",
			"message": _("Silakan login terlebih dahulu."),
		}

	status = get_current_member_status()
	if status == "verified":
		return {
			"status": status,
			"verified": True,
			"logged_out": False,
			"redirect_to": frappe.form_dict.get("redirect_to") or "/abk/submit-info",
			"message": _("Login berhasil."),
		}

	message_by_status = {
		"pending": _("Akun Anda sedang menunggu verifikasi admin. Silakan login kembali setelah akun diverifikasi."),
		"rejected": _("Akun Anda belum dapat digunakan. Silakan hubungi admin."),
		"missing": _("Akun Anda belum memiliki profil member ABK. Silakan daftar ulang atau hubungi admin."),
	}
	message = message_by_status.get(status, _("Akun Anda belum dapat mengakses fitur member."))

	frappe.local.login_manager.logout()
	return {
		"status": status,
		"verified": False,
		"logged_out": True,
		"redirect_to": f"/abk/login?status={status}",
		"message": message,
	}


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


from werkzeug.exceptions import HTTPException
from werkzeug.utils import redirect

def redirect_members_from_desk():
	if not hasattr(frappe.local, "request"):
		return

	path = frappe.local.request.path or ""

	if path in ("/login", "/login/") and frappe.local.request.method == "GET":
		raise HTTPException(response=redirect("/abk/login"))

	if not is_desk_route(path):
		return

	if frappe.session.user == "Guest":
		return

	if is_abk_admin_user(frappe.session.user):
		return

	if not is_frontend_only_user(frappe.session.user):
		return

	raise HTTPException(response=redirect("/abk"))


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

	if is_abk_admin_user(user) or user == "Administrator":
		return "app"

	return None


@frappe.whitelist()
def update_member_avatar(file_url):
	"""Update the logged-in user's profile picture."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login first."))

	file_url = cstr(file_url).strip()
	if not file_url:
		frappe.throw(_("File URL is required."))

	frappe.db.set_value("User", frappe.session.user, "user_image", file_url)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def update_member_profile(phone, city=None, district=None):
	"""Update phone and address for logged-in user's profile."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login first."))

	phone = strip_html(cstr(phone)).strip()
	city = strip_html(cstr(city)).strip()
	district = strip_html(cstr(district)).strip()

	if not phone:
		frappe.throw(_("Phone number is required."))
	if not validate_phone_number(phone):
		frappe.throw(_("Please enter a valid phone number."))

	profile_name = frappe.db.get_value("ABK Member Profile", {"user": frappe.session.user}, "name")
	if not profile_name:
		frappe.throw(_("Member profile not found."))

	frappe.db.set_value("ABK Member Profile", profile_name, {
		"phone": phone,
		"city": city,
		"district": district
	})
	return {"ok": True, "message": _("Profil berhasil diperbarui.")}


@frappe.whitelist()
def change_member_password(old_password, new_password):
	"""Change the logged-in member's password after verifying old password."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login first."))

	old_password = cstr(old_password)
	new_password = cstr(new_password)

	if not old_password or not new_password:
		frappe.throw(_("Old password and new password are required."))

	# Verify old password
	from frappe.utils.password import check_password
	try:
		check_password(frappe.session.user, old_password)
	except frappe.AuthenticationError:
		return {"ok": False, "message": _("Password lama tidak sesuai.")}

	# Update password using Frappe's built-in (enforces password policy)
	from frappe.utils.password import update_password
	try:
		update_password(frappe.session.user, new_password)
	except frappe.exceptions.ValidationError as e:
		return {"ok": False, "message": str(e) or _("Password baru tidak memenuhi syarat keamanan.")}
	except Exception as e:
		return {"ok": False, "message": _("Gagal mengganti password. Coba lagi.")}

	return {"ok": True, "message": _("Password berhasil diperbarui.")}


def _clean_text(value):
	return strip_html(cstr(value)).strip()


def _resolve_public_place(place_slug=None, abk_place=None):
	filters = {"published": 1, "verification_status": "Published"}
	if abk_place:
		filters["name"] = cstr(abk_place).strip()
	elif place_slug:
		filters["slug"] = cstr(place_slug).strip()
	else:
		frappe.throw(_("Tempat tidak ditemukan."))

	place = frappe.db.get_value("ABK Place", filters, ["name", "place_name"], as_dict=True)
	if not place:
		frappe.throw(_("Tempat tidak ditemukan atau belum dipublikasikan."))

	return place


def _resolve_experience_badges(badges):
	if isinstance(badges, str):
		badges = frappe.parse_json(badges or "[]")

	if not badges:
		return []

	if not isinstance(badges, list):
		frappe.throw(_("Pilihan badge tidak valid."))

	resolved = []
	seen = set()
	for badge in badges:
		badge_value = cstr(badge).strip()
		if not badge_value:
			continue

		name = frappe.db.get_value(
			"ABK Experience Badge",
			{"name": badge_value, "published": 1},
			"name",
		) or frappe.db.get_value(
			"ABK Experience Badge",
			{"slug": badge_value, "published": 1},
			"name",
		)
		if not name:
			frappe.throw(_("Badge tidak valid atau belum dipublikasikan."))

		if name not in seen:
			seen.add(name)
			resolved.append(name)

	return resolved


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def submit_place_experience(**kwargs):
	if frappe.session.user == "Guest":
		frappe.throw(_("Silakan login terlebih dahulu untuk membagikan pengalaman."), frappe.PermissionError)

	place = _resolve_public_place(
		place_slug=kwargs.get("place_slug"),
		abk_place=kwargs.get("abk_place"),
	)
	reviewer_relationship = cstr(kwargs.get("reviewer_relationship")).strip()
	if reviewer_relationship and reviewer_relationship not in RELATIONSHIP_OPTIONS:
		frappe.throw(_("Please choose a valid relationship."))

	experience_text = _clean_text(kwargs.get("experience_text"))
	if not experience_text:
		frappe.throw(_("Pengalaman wajib diisi."))

	reviewer_name = _clean_text(kwargs.get("reviewer_name"))
	if not reviewer_name:
		reviewer_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	visit_date = None
	if kwargs.get("visit_date"):
		visit_date = getdate(kwargs.get("visit_date"))

	doc = frappe.get_doc(
		{
			"doctype": "ABK Place Experience",
			"abk_place": place.name,
			"reviewer_user": frappe.session.user,
			"reviewer_name": reviewer_name,
			"reviewer_relationship": reviewer_relationship,
			"is_anonymous": 1 if cstr(kwargs.get("is_anonymous")).lower() in ("1", "true", "yes", "on") else 0,
			"experience_title": _clean_text(kwargs.get("experience_title")),
			"experience_text": experience_text,
			"helpful_points": _clean_text(kwargs.get("helpful_points")),
			"things_to_note": _clean_text(kwargs.get("things_to_note")),
			"visit_date": visit_date,
			"verification_status": "New",
			"published": 0,
		}
	)

	for badge in _resolve_experience_badges(kwargs.get("badges")):
		doc.append("badges", {"badge": badge})

	doc.owner = frappe.session.user
	doc.insert(ignore_permissions=True)

	return {
		"ok": True,
		"name": doc.name,
		"message": _("Terima kasih, pengalaman Anda sudah dikirim dan akan dicek admin."),
	}
