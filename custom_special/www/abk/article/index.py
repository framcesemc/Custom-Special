import frappe

from custom_special.abk_portal.public import get_published_article_by_slug, get_related_articles, raise_not_found


def get_context(context):
	context.no_cache = 1
	slug = frappe.form_dict.get("slug")
	context.article = get_published_article_by_slug(slug)

	if not context.article:
		raise_not_found()

	context.title = context.article.title
	context.description = context.article.intro
	context.image = context.article.cover_image
	context.author = context.article.author
	context.published_on = context.article.published_on
	context.related_articles = get_related_articles(context.article, limit=3)
	context.parents = [
		{"name": "ABK Portal", "route": "/abk"},
		{"name": "Articles", "route": "/abk/articles"},
	]
