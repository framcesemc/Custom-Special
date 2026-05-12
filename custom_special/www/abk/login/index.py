import frappe
from frappe import _

from custom_special.abk_portal.api import get_current_member_status


def get_context(context):
	context.no_cache = 1
	context.title = "Login Member ABK"

	# Jika sudah login, redirect sesuai kondisi user
	if frappe.session.user != "Guest":
		status = get_current_member_status()
		if status == "verified":
			frappe.local.flags.redirect_location = "/abk/submit-info"
			raise frappe.Redirect
		if status in ("pending", "rejected", "missing"):
			frappe.local.login_manager.logout()
			frappe.local.flags.redirect_location = f"/abk/login?status={status}"
			raise frappe.Redirect

	# Ambil redirect target dari query string, default ke /abk
	redirect_to = frappe.form_dict.get("redirect-to") or "/abk"
	context.redirect_to = redirect_to
	context.status_message = get_status_message()
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]


def get_status_message():
	status = frappe.form_dict.get("status")
	if status == "pending":
		return _("Akun Anda sedang menunggu verifikasi admin. Silakan login kembali setelah akun diverifikasi.")
	if status == "rejected":
		return _("Akun Anda belum dapat digunakan. Silakan hubungi admin.")
	if status == "missing":
		return _("Akun Anda belum memiliki profil member ABK. Silakan daftar ulang atau hubungi admin.")
	return ""
