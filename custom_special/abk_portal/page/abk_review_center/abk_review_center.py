import frappe
from frappe import _
from frappe.utils import now
import json

REVIEW_ROLES = {"System Manager", "ABK Admin"}

def get_context(context):
	context.no_cache = 1

@frappe.whitelist()
def get_review_center_data():
	require_review_admin()
	
	return {
		"summary": {
			"members": frappe.db.count("ABK Member Profile", {"verification_status": "Pending"}),
			"submitted_info": frappe.db.count("User Submitted Info", {"verification_status": ["in", ["New", "Reviewing"]]}),
			"experiences": frappe.db.count("ABK Place Experience", {"verification_status": ["in", ["New", "Reviewing"]]}),
			"inquiries": frappe.db.count("Parent Inquiry", {"status": ["in", ["New", "In Progress"]]}),
		}
	}

@frappe.whitelist()
def get_tabulator_data(section, page=1, size=20, filters=None, sort=None):
	require_review_admin()
	
	page = int(page)
	size = int(size)
	limit_start = (page - 1) * size

	# Parse Tabulator filters and sorters
	parsed_filters = []
	if filters:
		if isinstance(filters, str):
			filters = json.loads(filters)
		for f in filters:
			field = f.get('field')
			type_ = f.get('type')
			value = f.get('value')
			if type_ == "like":
				parsed_filters.append([field, "like", f"%{value}%"])
			elif type_ == "=":
				parsed_filters.append([field, "=", value])

	order_by = "creation desc"
	if sort:
		if isinstance(sort, str):
			sort = json.loads(sort)
		if sort:
			s = sort[0]
			order_by = f"{s.get('field')} {s.get('dir')}"

	if section == "members":
		base_filters = [["verification_status", "=", "Pending"]]
		fields = ["name", "full_name", "phone", "relationship", "city", "creation"]
		doctype = "ABK Member Profile"
	elif section == "submitted_info":
		base_filters = [["verification_status", "in", ["New", "Reviewing"]]]
		fields = ["name", "place_name", "suggested_category", "city", "submitter_name", "creation"]
		doctype = "User Submitted Info"
	elif section == "experiences":
		base_filters = [["verification_status", "in", ["New", "Reviewing"]]]
		fields = ["name", "abk_place", "reviewer_name", "reviewer_relationship", "experience_title", "creation"]
		doctype = "ABK Place Experience"
	elif section == "inquiries":
		base_filters = [["status", "in", ["New", "In Progress"]]]
		fields = ["name", "parent_name", "phone", "inquiry_type", "city", "status", "creation"]
		doctype = "Parent Inquiry"
	else:
		frappe.throw(_("Unknown section"))

	final_filters = base_filters + parsed_filters

	rows = frappe.get_all(
		doctype,
		filters=final_filters,
		fields=fields,
		order_by=order_by,
		limit_start=limit_start,
		limit_page_length=size
	)
	
	if section == "submitted_info":
		for row in rows:
			row.info_type = row.suggested_category

	total_count = frappe.db.count(doctype, filters=final_filters)
	last_page = (total_count + size - 1) // size

	return {
		"last_page": last_page,
		"data": rows
	}

@frappe.whitelist()
def review_action(section, action, name):
	require_review_admin()

	if section == "members":
		return review_member(action, name)
	if section == "submitted_info":
		return review_submitted_info(action, name)
	if section == "experiences":
		return review_experience(action, name)
	if section == "inquiries":
		return review_parent_inquiry(action, name)

	frappe.throw(_("Unknown review section."), frappe.ValidationError)

def review_member(action, name):
	if action == "verify":
		from custom_special.abk_portal.doctype.abk_member_profile.abk_member_profile import verify_member
		return verify_member(name)
	if action == "reject":
		from custom_special.abk_portal.doctype.abk_member_profile.abk_member_profile import reject_member
		return reject_member(name)
	frappe.throw(_("Unknown member action."), frappe.ValidationError)

def review_submitted_info(action, name):
	if action == "approve":
		from custom_special.abk_portal.doctype.user_submitted_info.user_submitted_info import approve_and_create_abk_place
		return approve_and_create_abk_place(name)
	if action == "reject":
		from custom_special.abk_portal.doctype.user_submitted_info.user_submitted_info import reject_submission
		return reject_submission(name)
	frappe.throw(_("Unknown submitted info action."), frappe.ValidationError)

def review_experience(action, name):
	if action == "approve":
		from custom_special.abk_portal.doctype.abk_place_experience.abk_place_experience import approve_experience
		return approve_experience(name)
	if action == "reject":
		from custom_special.abk_portal.doctype.abk_place_experience.abk_place_experience import reject_experience
		return reject_experience(name)
	frappe.throw(_("Unknown experience action."), frappe.ValidationError)

def review_parent_inquiry(action, name):
	inquiry = frappe.get_doc("Parent Inquiry", name)
	if action == "in_progress":
		inquiry.db_set({"status": "In Progress", "follow_up_notes": append_follow_up_note(inquiry, _("Marked In Progress."))})
		return {"name": inquiry.name, "status": "In Progress"}
	if action == "contacted":
		inquiry.db_set({"status": "Contacted", "follow_up_notes": append_follow_up_note(inquiry, _("Marked contacted."))})
		return {"name": inquiry.name, "status": "Contacted"}
	if action == "close":
		inquiry.db_set({"status": "Closed", "follow_up_notes": append_follow_up_note(inquiry, _("Closed."))})
		return {"name": inquiry.name, "status": "Closed"}
	frappe.throw(_("Unknown inquiry action."), frappe.ValidationError)

def append_follow_up_note(doc, note):
	existing = doc.follow_up_notes or ""
	stamp = _("{0} by {1}: {2}").format(now(), frappe.session.user, note)
	return f"{existing}<p>{frappe.utils.escape_html(stamp)}</p>" if existing else f"<p>{frappe.utils.escape_html(stamp)}</p>"

def require_review_admin():
	if frappe.session.user == "Administrator":
		return
	if not REVIEW_ROLES.intersection(set(frappe.get_roles())):
		frappe.throw(_("Only System Manager or ABK Admin can access ABK Review Center."), frappe.PermissionError)
