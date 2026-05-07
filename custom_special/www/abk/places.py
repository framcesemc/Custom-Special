import frappe

from custom_special.abk_portal.public import get_distinct_values, get_filter_value, get_published_places

sitemap = 1


def get_context(context):
	context.no_cache = 1
	context.title = "ABK Places"
	context.places = get_published_places(limit=50)
	context.cities = get_distinct_values("ABK Place", "city")
	context.districts = get_distinct_values("ABK Place", "district")
	context.place_types = ["School", "Therapy Center", "ABK Friendly Place"]
	context.filters = frappe._dict(
		q=get_filter_value("q"),
		city=get_filter_value("city"),
		district=get_filter_value("district"),
		place_type=get_filter_value("place_type"),
	)
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]
