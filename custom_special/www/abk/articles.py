import frappe

from custom_special.abk_portal.public import (
	blog_post_doctype_exists,
	get_article_categories,
	get_article_tags,
	get_filter_value,
	get_published_articles,
)

sitemap = 1


def get_context(context):
	context.no_cache = 1
	context.title = "ABK Articles"
	context.description = "Artikel edukasi tepercaya untuk orang tua anak berkebutuhan khusus."
	context.articles = get_published_articles(limit=60)
	context.categories = get_article_categories()
	context.tags = get_article_tags()
	context.blog_enabled = blog_post_doctype_exists()
	context.filters = frappe._dict(
		q=get_filter_value("q"),
		category=get_filter_value("category"),
		tag=get_filter_value("tag"),
	)
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]
