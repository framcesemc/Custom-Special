import frappe

from custom_special.abk_portal.public import (
	get_place_experience_summary,
	get_published_experience_badges,
	get_published_place_by_slug,
	get_published_place_experiences,
	get_published_place_gallery,
	raise_not_found,
)


def get_context(context):
	context.no_cache = 1
	slug = frappe.form_dict.get("slug")
	context.place = get_published_place_by_slug(slug)

	if not context.place:
		raise_not_found()

	context.title = context.place.place_name
	context.place_description = context.place.full_description or context.place.short_description
	context.gallery = get_published_place_gallery(context.place)
	context.experiences = get_published_place_experiences(context.place)
	context.experience_summary = get_place_experience_summary(context.experiences)
	context.experience_badges = get_published_experience_badges()
	context.is_guest = frappe.session.user == "Guest"
	context.parents = [
		{"name": "ABK Portal", "route": "/abk"},
		{"name": "Places", "route": "/abk/places"},
	]
