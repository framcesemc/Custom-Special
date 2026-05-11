import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cstr, strip_html


ABK_ARTICLE_CATEGORIES = [
	"Parenting",
	"Therapy",
	"Education",
	"Inclusive School",
	"Sensory Friendly",
	"Activities",
	"Health",
	"Community",
]

ARTICLE_FALLBACK_COVER = (
	"https://images.unsplash.com/photo-1604881991720-f91add269bed"
	"?auto=format&fit=crop&w=1200&q=80"
)


PUBLIC_PLACE_FIELDS = [
	"name",
	"modified",
	"slug",
	"place_name",
	"place_type",
	"city",
	"district",
	"address",
	"google_map_url",
	"short_description",
	"plus_points",
	"minus_points",
	"special_needs_tags",
	"cover_image",
]

PUBLIC_TEACHER_FIELDS = [
	"name",
	"modified",
	"slug",
	"teacher_name",
	"city",
	"district",
	"service_area",
	"specialization_tags",
	"profile_summary",
	"tariff_range",
	"public_photo",
]


def get_filter_value(fieldname: str) -> str:
	return cstr(frappe.form_dict.get(fieldname)).strip()


def blog_post_doctype_exists() -> bool:
	return bool(frappe.db.exists("DocType", "Blog Post"))


def blog_category_doctype_exists() -> bool:
	return bool(frappe.db.exists("DocType", "Blog Category"))


def _get_blog_meta():
	if not blog_post_doctype_exists():
		return None

	return frappe.get_meta("Blog Post")


def _first_existing_field(meta, candidates):
	for fieldname in candidates:
		if meta.has_field(fieldname):
			return fieldname


def _get_blog_post_fields(meta, include_content=False):
	fields = ["name", "creation", "modified"]
	for candidate_group in (
		("title",),
		("route",),
		("blog_category", "category"),
		("blogger", "author"),
		("published_on", "publish_date"),
		("blog_intro", "intro", "description"),
		("meta_description",),
		("meta_image", "cover_image", "image", "featured_image"),
		("article_tags",),
		("featured", "is_featured"),
	):
		fieldname = _first_existing_field(meta, candidate_group)
		if fieldname and fieldname not in fields:
			fields.append(fieldname)

	if include_content:
		for candidate_group in (("content", "content_html"), ("meta_title",)):
			fieldname = _first_existing_field(meta, candidate_group)
			if fieldname and fieldname not in fields:
				fields.append(fieldname)

	return fields


def _get_blog_post_filters(meta):
	filters = {}
	if meta.has_field("published"):
		filters["published"] = 1

	category_field = _first_existing_field(meta, ("blog_category", "category"))
	category = get_filter_value("category")
	if category_field:
		filters[category_field] = category if category else ["in", ABK_ARTICLE_CATEGORIES]

	tag = get_filter_value("tag")
	if tag and meta.has_field("article_tags"):
		filters["article_tags"] = ["like", f"%{tag}%"]

	return filters


def _get_blog_post_or_filters(meta):
	keyword = get_filter_value("q")
	if not keyword:
		return None

	like_value = f"%{keyword}%"
	or_filters = {}
	for fieldname in ("title", "blog_intro", "intro", "description", "content", "content_html", "article_tags"):
		if meta.has_field(fieldname):
			or_filters[fieldname] = ["like", like_value]
	return or_filters


def _split_article_tags(article_tags):
	return [
		tag.strip()
		for tag in cstr(article_tags).split(",")
		if tag and tag.strip()
	]


def _tag_matches(article, selected_tag):
	if not selected_tag:
		return True

	selected_tag = cstr(selected_tag).strip().lower()
	return selected_tag in {tag.lower() for tag in article.tags}


def _article_slug(article):
	route = cstr(article.get("route")).strip("/")
	if route:
		return route.split("/")[-1]

	return cstr(article.get("name")).strip()


def _normalize_article(row):
	title = row.get("title") or row.get("name")
	intro = row.get("blog_intro") or row.get("intro") or row.get("description") or row.get("meta_description")
	cover_image = (
		row.get("meta_image")
		or row.get("cover_image")
		or row.get("image")
		or row.get("featured_image")
		or ARTICLE_FALLBACK_COVER
	)
	published_on = row.get("published_on") or row.get("publish_date") or row.get("creation")
	category = row.get("blog_category") or row.get("category")
	content = row.get("content") or row.get("content_html") or ""
	tags = _split_article_tags(row.get("article_tags"))

	article = frappe._dict(row)
	article.update(
		{
			"title": title,
			"slug": _article_slug(row),
			"cover_image": cover_image,
			"author": row.get("blogger") or row.get("author") or "ABK Portal",
			"category": category,
			"published_on": published_on,
			"intro": strip_html(cstr(intro)) if intro else "",
			"content": content,
			"tags": tags,
			"is_featured": row.get("featured") or row.get("is_featured"),
		}
	)
	return article


def get_article_categories():
	return ABK_ARTICLE_CATEGORIES


def get_published_articles(limit: int = 20, filters_from_request: bool = True):
	meta = _get_blog_meta()
	if not meta:
		return []

	filters = _get_blog_post_filters(meta) if filters_from_request else {}
	if not filters_from_request and meta.has_field("published"):
		filters["published"] = 1

	category_field = _first_existing_field(meta, ("blog_category", "category"))
	if not filters_from_request and category_field:
		filters[category_field] = ["in", ABK_ARTICLE_CATEGORIES]

	order_field = _first_existing_field(meta, ("published_on", "publish_date")) or "creation"
	selected_tag = get_filter_value("tag") if filters_from_request and meta.has_field("article_tags") else ""
	rows = frappe.db.get_all(
		"Blog Post",
		fields=_get_blog_post_fields(meta),
		filters=filters,
		or_filters=_get_blog_post_or_filters(meta) if filters_from_request else None,
		order_by=f"{order_field} desc",
		limit_page_length=limit * 4 if selected_tag else limit,
	)
	articles = [_normalize_article(row) for row in rows]
	if selected_tag:
		articles = [article for article in articles if _tag_matches(article, selected_tag)]
	return articles[:limit]


def get_featured_articles(limit: int = 3):
	meta = _get_blog_meta()
	if not meta:
		return []

	filters = {}
	if meta.has_field("published"):
		filters["published"] = 1

	category_field = _first_existing_field(meta, ("blog_category", "category"))
	if category_field:
		filters[category_field] = ["in", ABK_ARTICLE_CATEGORIES]

	featured_field = _first_existing_field(meta, ("featured", "is_featured"))
	if featured_field:
		filters[featured_field] = 1

	order_field = _first_existing_field(meta, ("published_on", "publish_date")) or "creation"
	rows = frappe.db.get_all(
		"Blog Post",
		fields=_get_blog_post_fields(meta),
		filters=filters,
		order_by=f"{order_field} desc",
		limit_page_length=limit,
	)

	if not rows:
		return get_published_articles(limit=limit, filters_from_request=False)

	return [_normalize_article(row) for row in rows]


def get_article_tags():
	meta = _get_blog_meta()
	if not meta or not meta.has_field("article_tags"):
		return []

	filters = {}
	if meta.has_field("published"):
		filters["published"] = 1

	category_field = _first_existing_field(meta, ("blog_category", "category"))
	if category_field:
		filters[category_field] = ["in", ABK_ARTICLE_CATEGORIES]

	rows = frappe.db.get_all(
		"Blog Post",
		filters=filters,
		fields=["article_tags"],
		limit_page_length=500,
	)
	tags = []
	seen = set()
	for row in rows:
		for tag in _split_article_tags(row.article_tags):
			normalized_tag = tag.lower()
			if normalized_tag in seen:
				continue
			seen.add(normalized_tag)
			tags.append(tag)

	return sorted(tags, key=lambda tag: tag.lower())


def get_published_article_by_slug(slug: str):
	meta = _get_blog_meta()
	if not meta or not slug:
		return None

	filters = {}
	if meta.has_field("published"):
		filters["published"] = 1

	category_field = _first_existing_field(meta, ("blog_category", "category"))
	if category_field:
		filters[category_field] = ["in", ABK_ARTICLE_CATEGORIES]

	rows = frappe.db.get_all(
		"Blog Post",
		fields=_get_blog_post_fields(meta, include_content=True),
		filters=filters,
		order_by="modified desc",
		limit_page_length=100,
	)

	for article in [_normalize_article(row) for row in rows]:
		if article.slug == slug or article.name == slug or cstr(article.get("route")).strip("/") == slug:
			return article

	return None


def get_related_articles(article, limit: int = 3):
	meta = _get_blog_meta()
	if not meta or not article:
		return []

	order_field = _first_existing_field(meta, ("published_on", "publish_date")) or "creation"
	filters = {"name": ["!=", article.name]}
	if meta.has_field("published"):
		filters["published"] = 1

	category_field = _first_existing_field(meta, ("blog_category", "category"))
	if category_field:
		filters[category_field] = ["in", ABK_ARTICLE_CATEGORIES]

	rows = frappe.db.get_all(
		"Blog Post",
		fields=_get_blog_post_fields(meta),
		filters=filters,
		order_by=f"{order_field} desc",
		limit_page_length=60,
	)
	article_tags = {tag.lower() for tag in article.tags}
	related_articles = []
	for related in [_normalize_article(row) for row in rows]:
		shared_tags = article_tags.intersection({tag.lower() for tag in related.tags})
		same_category = related.category and related.category == article.category
		if not same_category and not shared_tags:
			continue

		related.related_score = (2 if same_category else 0) + len(shared_tags)
		related_articles.append(related)

	related_articles.sort(
		key=lambda related: (related.related_score, related.published_on or related.creation),
		reverse=True,
	)
	return related_articles[:limit]


def get_published_places(limit: int = 20):
	filters = {
		"published": 1,
		"verification_status": "Published",
	}

	for fieldname in ("city", "district", "place_type"):
		if value := get_filter_value(fieldname):
			filters[fieldname] = value

	or_filters = None
	if keyword := get_filter_value("q"):
		like_value = f"%{keyword}%"
		or_filters = {
			"place_name": ["like", like_value],
			"short_description": ["like", like_value],
			"special_needs_tags": ["like", like_value],
			"city": ["like", like_value],
			"district": ["like", like_value],
		}

	return frappe.db.get_all(
		"ABK Place",
		fields=PUBLIC_PLACE_FIELDS,
		filters=filters,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)


def get_published_teachers(limit: int = 20):
	filters = {
		"published": 1,
		"verification_status": "Published",
	}

	for fieldname in ("city", "district"):
		if value := get_filter_value(fieldname):
			filters[fieldname] = value

	or_filters = None
	if keyword := get_filter_value("q"):
		like_value = f"%{keyword}%"
		or_filters = {
			"teacher_name": ["like", like_value],
			"profile_summary": ["like", like_value],
			"specialization_tags": ["like", like_value],
			"service_area": ["like", like_value],
			"city": ["like", like_value],
			"district": ["like", like_value],
		}

	return frappe.db.get_all(
		"Shadow Teacher",
		fields=PUBLIC_TEACHER_FIELDS,
		filters=filters,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)


def get_distinct_values(doctype: str, fieldname: str):
	rows = frappe.db.get_all(
		doctype,
		fields=[fieldname],
		filters={"published": 1, "verification_status": "Published"},
		group_by=fieldname,
		order_by=f"{fieldname} asc",
	)
	return [row[fieldname] for row in rows if row.get(fieldname)]


def get_published_place_by_slug(slug: str):
	return frappe.db.get_value(
		"ABK Place",
		{"slug": slug, "published": 1, "verification_status": "Published"},
		PUBLIC_PLACE_FIELDS,
		as_dict=True,
	)


def get_published_teacher_by_slug(slug: str):
	return frappe.db.get_value(
		"Shadow Teacher",
		{"slug": slug, "published": 1, "verification_status": "Published"},
		PUBLIC_TEACHER_FIELDS,
		as_dict=True,
	)


def raise_not_found():
	frappe.local.flags.redirect_location = "/404"
	raise frappe.Redirect


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=60 * 60)
def submit_parent_inquiry(
	parent_name,
	phone,
	inquiry_type="General",
	city=None,
	district=None,
	message=None,
	related_place=None,
	related_teacher=None,
):
	parent_name = strip_html(cstr(parent_name)).strip()
	phone = strip_html(cstr(phone)).strip()

	if not parent_name or not phone:
		frappe.throw(_("Name and phone are required."))

	doc = frappe.get_doc(
		{
			"doctype": "Parent Inquiry",
			"parent_name": parent_name,
			"phone": phone,
			"inquiry_type": inquiry_type or "General",
			"city": strip_html(cstr(city)).strip(),
			"district": strip_html(cstr(district)).strip(),
			"message": message,
			"related_place": related_place,
			"related_teacher": related_teacher,
			"status": "New",
		}
	)
	doc.insert(ignore_permissions=True)

	return {"name": doc.name}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60 * 60)
def submit_user_submitted_info(**kwargs):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to submit information."))

	from custom_special.abk_portal.api import require_verified_member

	require_verified_member()

	media_rows = frappe.parse_json(kwargs.get("media") or "[]")
	data = {
		"doctype": "User Submitted Info",
		"submitter_name": strip_html(cstr(kwargs.get("submitter_name")).strip()),
		"submitter_phone": strip_html(cstr(kwargs.get("submitter_phone")).strip()),
		"submitter_email": strip_html(cstr(kwargs.get("submitter_email")).strip()),
		"submitter_relationship": kwargs.get("submitter_relationship"),
		"confirmation_notes": kwargs.get("confirmation_notes"),
		"place_name": strip_html(cstr(kwargs.get("place_name")).strip()),
		"suggested_category": kwargs.get("suggested_category"),
		"city": strip_html(cstr(kwargs.get("city")).strip()),
		"district": strip_html(cstr(kwargs.get("district")).strip()),
		"area": strip_html(cstr(kwargs.get("area")).strip()),
		"address": strip_html(cstr(kwargs.get("address")).strip()),
		"google_map_url": strip_html(cstr(kwargs.get("google_map_url")).strip()),
		"contact_phone": strip_html(cstr(kwargs.get("contact_phone")).strip()),
		"contact_whatsapp": strip_html(cstr(kwargs.get("contact_whatsapp")).strip()),
		"contact_email": strip_html(cstr(kwargs.get("contact_email")).strip()),
		"website_url": strip_html(cstr(kwargs.get("website_url")).strip()),
		"instagram_url": strip_html(cstr(kwargs.get("instagram_url")).strip()),
		"reference_url": strip_html(cstr(kwargs.get("reference_url")).strip()),
		"reference_notes": kwargs.get("reference_notes"),
		"description": kwargs.get("description"),
		"plus_points": kwargs.get("plus_points"),
		"minus_points": kwargs.get("minus_points"),
		"verification_status": "New",
	}

	if not data["place_name"] or not data["suggested_category"] or not data["city"]:
		frappe.throw(_("Place name, category, and city are required."))

	doc = frappe.get_doc(data)
	for row in media_rows:
		if not isinstance(row, dict):
			continue

		media_type = row.get("media_type")
		media_url = strip_html(cstr(row.get("media_url")).strip())
		caption = strip_html(cstr(row.get("caption")).strip())
		if not media_type and not media_url and not caption:
			continue

		doc.append(
			"media",
			{
				"media_type": media_type,
				"media_url": media_url,
				"caption": caption,
				"sort_order": row.get("sort_order"),
			},
		)

	doc.insert()

	return {"name": doc.name}


@frappe.whitelist()
def submit_place_draft(**kwargs):
	return submit_user_submitted_info(**kwargs)


@frappe.whitelist()
def append_submission_media(name, media_type, media_file=None, media_url=None, caption=None, sort_order=None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to add media."))

	doc = frappe.get_doc("User Submitted Info", name)
	is_admin = "ABK Admin" in frappe.get_roles() or "System Manager" in frappe.get_roles()
	if doc.owner != frappe.session.user and not is_admin:
		frappe.throw(_("You can only add media to your own submission."), frappe.PermissionError)
	if doc.verification_status != "New" and not is_admin:
		frappe.throw(_("Media can only be added before admin review."))

	doc.append(
		"media",
		{
			"media_type": media_type,
			"media_file": media_file,
			"media_url": media_url,
			"caption": strip_html(cstr(caption)).strip(),
			"sort_order": sort_order,
		},
	)
	doc.save(ignore_permissions=True)

	return {"name": doc.name}
