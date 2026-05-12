import frappe
from frappe import _

from custom_special.abk_portal.api import get_current_member_status, is_frontend_only_user


def get_context(context):
    context.no_cache = 1
    context.title = "Login Member ABK"

    # Jika sudah login, redirect sesuai kondisi user
    if frappe.session.user != "Guest":
        status = get_current_member_status()
        if status == "verified":
            frappe.local.flags.redirect_location = "/abk/submit-info"
            raise frappe.Redirect
        elif status in ("pending", "rejected", "missing"):
            frappe.local.flags.redirect_location = "/abk"
            raise frappe.Redirect

    # Ambil redirect target dari query string, default ke /abk
    redirect_to = frappe.form_dict.get("redirect-to") or "/abk"
    context.redirect_to = redirect_to
    context.parents = [{"name": "ABK Portal", "route": "/abk"}]
