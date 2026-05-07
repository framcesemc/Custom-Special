import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cstr, strip_html


PUBLIC_PLACE_FIELDS = [
	"name",
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
