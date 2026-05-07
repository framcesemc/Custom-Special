import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cstr, strip_html


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
