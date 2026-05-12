import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html, now

from custom_special.abk_portal.media import get_media_kind, validate_media_row
from custom_special.abk_portal.notifications import notify_system_managers


ADMIN_ROLES = {"ABK Admin", "System Manager"}


class UserSubmittedInfo(Document):
	def before_insert(self):
		if not self.verification_status:
			self.verification_status = "New"

	def after_insert(self):
		notify_system_managers(
			"Info tempat baru menunggu verifikasi",
			"Ada referensi ABK Place baru yang dikirim user.",
			self.doctype,
			self.name,
		)

	def validate(self):
		if self.is_new() and self.verification_status != "New" and not has_abk_admin_role():
			frappe.throw(_("Submitted info must start as New."))
		if self.is_new() and not has_abk_admin_role():
			for fieldname in ("approved_place", "reviewed_by", "reviewed_on", "admin_notes"):
				if self.get(fieldname):
					frappe.throw(_("Admin review fields can only be set by ABK Admin."))
		for row in self.get("media") or []:
			validate_media_row(row)


def has_abk_admin_role():
	return bool(ADMIN_ROLES.intersection(set(frappe.get_roles())))


def require_abk_admin_role():
	if not has_abk_admin_role():
		frappe.throw(_("Only ABK Admin or System Manager can perform this action."), frappe.PermissionError)


@frappe.whitelist()
def approve_and_create_abk_place(name):
	require_abk_admin_role()

	submission = frappe.get_doc("User Submitted Info", name)
	if submission.approved_place:
		return {"place": submission.approved_place}

	if submission.suggested_category not in ("School", "Therapy Center", "ABK Friendly Place"):
		frappe.throw(_("Only place submissions can be converted to ABK Place."))

	place = frappe.new_doc("ABK Place")
	place.place_name = submission.place_name
	place.place_type = submission.suggested_category
	place.city = submission.city
	place.district = submission.district
	place.area = submission.area
	place.address = submission.address
	place.google_map_url = submission.google_map_url
	place.short_description = submission.description
	place.plus_points = submission.plus_points
	place.minus_points = submission.minus_points
	place.published = 1
	place.verification_status = "Published"
	place.admin_notes = build_admin_notes(submission)

	for media in submission.media:
		media_source = media.media_file or media.media_url
		if get_media_kind(media_source) == "Image" and media.media_file:
			place.cover_image = media.media_file
			break

	for media in submission.media:
		media_source = media.media_file or media.media_url
		if not media_source:
			continue

		place.append(
			"gallery",
			{
				"media_type": media.media_type or get_media_kind(media_source),
				"media_file": media.media_file,
				"media_url": media.media_url,
				"caption": media.caption,
				"sort_order": media.sort_order,
			},
		)

	place.insert(ignore_permissions=True)

	submission.db_set(
		{
			"verification_status": "Approved",
			"approved_place": place.name,
			"reviewed_by": frappe.session.user,
			"reviewed_on": now(),
		}
	)

	return {"place": place.name}


@frappe.whitelist()
def reject_submission(name):
	require_abk_admin_role()

	submission = frappe.get_doc("User Submitted Info", name)
	submission.db_set(
		{
			"verification_status": "Rejected",
			"reviewed_by": frappe.session.user,
			"reviewed_on": now(),
		}
	)

	return {"name": submission.name}


def build_admin_notes(submission):
	notes = []
	for label, value in (
		("Submitter", submission.submitter_name),
		("Submitter Phone", submission.submitter_phone),
		("Submitter Email", submission.submitter_email),
		("Relationship", submission.submitter_relationship),
		("Contact Phone", submission.contact_phone),
		("Contact WhatsApp", submission.contact_whatsapp),
		("Contact Email", submission.contact_email),
		("Website", submission.website_url),
		("Instagram", submission.instagram_url),
		("Reference URL", submission.reference_url),
		("Reference Notes", submission.reference_notes),
		("Confirmation Notes", submission.confirmation_notes),
	):
		if value:
			notes.append(f"<p><strong>{escape_html(label)}:</strong> {escape_html(value)}</p>")

	if submission.media:
		media_notes = []
		for row in submission.media:
			value = row.media_file or row.media_url
			if value:
				media_notes.append(f"{row.media_type or 'Media'}: {value}")

		if media_notes:
			notes.append("<p><strong>Media:</strong><br>" + "<br>".join(map(escape_html, media_notes)) + "</p>")

	return "\n".join(notes)
