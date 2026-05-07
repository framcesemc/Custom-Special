import frappe

from custom_special.abk_portal.public import get_published_place_by_slug, raise_not_found


def get_context(context):
	context.no_cache = 1
	slug = frappe.form_dict.get("slug")
	context.place = get_published_place_by_slug(slug)

	if not context.place:
		raise_not_found()

	context.title = context.place.place_name
	context.parents = [
		{"name": "ABK Portal", "route": "/abk"},
		{"name": "Places", "route": "/abk/places"},
	]
