from custom_special.abk_portal.public import (
	get_distinct_values,
	get_featured_articles,
	get_published_articles,
	get_published_places,
	get_published_teachers,
)

sitemap = 1


def get_context(context):
	context.no_cache = 1
	context.title = "ABK Portal"
	context.cities = sorted(
		set(get_distinct_values("ABK Place", "city") + get_distinct_values("Shadow Teacher", "city"))
	)
	context.featured_places = get_published_places(limit=3)
	context.featured_teachers = get_published_teachers(limit=3)
	context.latest_articles = get_published_articles(limit=3, filters_from_request=False)
	context.featured_articles = get_featured_articles(limit=3)
	context.parents = [{"name": "Home", "route": "/"}]
