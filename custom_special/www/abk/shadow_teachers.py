import frappe

from custom_special.abk_portal.public import get_distinct_values, get_filter_value, get_published_teachers

sitemap = 1


def get_context(context):
	context.no_cache = 1
	context.title = "Shadow Teachers"
	context.teachers = get_published_teachers(limit=50)
	context.cities = get_distinct_values("Shadow Teacher", "city")
	context.districts = get_distinct_values("Shadow Teacher", "district")
	context.filters = frappe._dict(
		q=get_filter_value("q"),
		city=get_filter_value("city"),
		district=get_filter_value("district"),
	)
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]
