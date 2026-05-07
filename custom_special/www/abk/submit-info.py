import frappe


def get_context(context):
	context.no_cache = 1
	context.title = "Bagikan Info Tempat"
	context.is_guest = frappe.session.user == "Guest"
	context.place_types = ["School", "Therapy Center", "ABK Friendly Place", "Shadow Teacher", "Tips"]
	context.relationships = ["Parent", "Guardian", "Teacher", "Therapist", "School Staff", "Other"]
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]
