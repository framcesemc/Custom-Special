import frappe

from custom_special.abk_portal.public import ABK_ARTICLE_CATEGORIES


ABK_EXPERIENCE_BADGES = [
	("Ramah Sensory", "Sensory", "Lingkungan terasa mendukung untuk kebutuhan sensory."),
	("Ruang Tunggu Nyaman", "Facility", "Area tunggu cukup nyaman untuk anak dan pendamping."),
	("Staff Komunikatif", "Service", "Staff mudah diajak komunikasi dan responsif."),
	("Guru/Terapis Sabar", "Service", "Guru atau terapis sabar mendampingi anak."),
	("Tidak Terlalu Ramai", "Sensory", "Suasana relatif tidak terlalu ramai."),
	("Cocok untuk Early Intervention", "Learning", "Cocok untuk dukungan intervensi dini."),
	("Cocok untuk Anak Non-Verbal", "Learning", "Pendekatan mendukung anak non-verbal."),
	("Akses Kursi Roda", "Accessibility", "Akses tempat mendukung kursi roda."),
	("Parkir Mudah", "Facility", "Akses parkir relatif mudah."),
	("Toilet Bersih", "Facility", "Toilet bersih dan nyaman digunakan."),
	("Jadwal Fleksibel", "Service", "Pengaturan jadwal relatif fleksibel."),
	("Admin Responsif", "Service", "Admin mudah dihubungi dan responsif."),
]


def after_install():
	create_abk_admin_role()
	create_abk_article_categories()
	create_abk_article_tags_field()
	create_abk_experience_badges()


def create_abk_admin_role():
	if frappe.db.exists("Role", "ABK Admin"):
		return

	role = frappe.new_doc("Role")
	role.role_name = "ABK Admin"
	role.desk_access = 1
	role.insert(ignore_permissions=True)


def create_abk_article_categories():
	if not frappe.db.exists("DocType", "Blog Category"):
		return

	for category in ABK_ARTICLE_CATEGORIES:
		# generate name seperti: Inclusive School -> inclusive-school
		category_name = frappe.scrub(category).replace("_", "-")

		# cek berdasarkan name / primary key
		if frappe.db.exists("Blog Category", category_name):
			continue

		doc = frappe.new_doc("Blog Category")
		doc.title = category
		doc.name = category_name

		doc.insert(
			ignore_permissions=True,
			ignore_if_duplicate=True
		)


def create_abk_article_tags_field():
	if not frappe.db.exists("DocType", "Blog Post"):
		return

	if frappe.db.exists("Custom Field", {"dt": "Blog Post", "fieldname": "article_tags"}):
		return

	insert_after = "blog_intro"
	meta = frappe.get_meta("Blog Post")
	if not meta.has_field(insert_after):
		insert_after = "blog_category" if meta.has_field("blog_category") else "title"

	field = frappe.new_doc("Custom Field")
	field.dt = "Blog Post"
	field.fieldname = "article_tags"
	field.label = "Article Tags"
	field.fieldtype = "Small Text"
	field.insert_after = insert_after
	field.description = "Comma-separated frontend tags, for example: autism, sensory friendly, sekolah inklusi"
	field.insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Blog Post")


def create_abk_experience_badges():
	if not frappe.db.exists("DocType", "ABK Experience Badge"):
		return

	for badge_name, badge_group, description in ABK_EXPERIENCE_BADGES:
		if frappe.db.exists("ABK Experience Badge", {"badge_name": badge_name}):
			continue

		doc = frappe.new_doc("ABK Experience Badge")
		doc.badge_name = badge_name
		doc.badge_group = badge_group
		doc.description = description
		doc.published = 1
		doc.insert(ignore_permissions=True)
