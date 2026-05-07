import frappe

from custom_special.abk_portal.public import get_published_teacher_by_slug, raise_not_found


def get_context(context):
	context.no_cache = 1
	slug = frappe.form_dict.get("slug")
	context.teacher = get_published_teacher_by_slug(slug)

	if not context.teacher:
		raise_not_found()

	context.title = context.teacher.teacher_name
	context.parents = [
		{"name": "ABK Portal", "route": "/abk"},
		{"name": "Shadow Teachers", "route": "/abk/shadow-teachers"},
	]
