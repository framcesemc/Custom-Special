import frappe


def after_install():
	create_abk_admin_role()


def create_abk_admin_role():
	if frappe.db.exists("Role", "ABK Admin"):
		return

	role = frappe.new_doc("Role")
	role.role_name = "ABK Admin"
	role.desk_access = 1
	role.insert(ignore_permissions=True)
