import re

import frappe


def make_unique_slug(doctype: str, value: str, current_name: str | None = None) -> str:
	base = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
	base = base or "item"
	slug = base
	counter = 2

	while True:
		existing_name = frappe.db.get_value(doctype, {"slug": slug}, "name")
		if not existing_name or existing_name == current_name:
			return slug

		slug = f"{base}-{counter}"
		counter += 1
