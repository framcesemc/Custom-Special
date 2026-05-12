import frappe

from custom_special.abk_portal.api import get_current_member_profile, get_current_member_status


def get_context(context):
	context.no_cache = 1
	context.title = "Bagikan Info Tempat"
	context.is_guest = frappe.session.user == "Guest"
	context.member_status = get_current_member_status()
	context.member_profile = get_current_member_profile()
	context.place_types = ["School", "Therapy Center", "ABK Friendly Place", "Shadow Teacher", "Tips"]
	context.relationships = ["Parent", "Guardian", "Teacher", "Therapist", "School Staff", "Other"]
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]
