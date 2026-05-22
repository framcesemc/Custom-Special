frappe.pages["abk-review-center"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("ABK Review Center"),
		single_column: true,
	});

	frappe.breadcrumbs.add("ABK Portal");
	page.add_inner_button(__("Refresh"), () => load_review_center(page));
	page.add_inner_button(__("Settings"), () => {
		frappe.set_route("Form", "ABK Portal Settings", "ABK Portal Settings");
	});
	page.body.addClass("abk-review-center-page");
	
	// Load Tabulator CSS and JS if not already loaded
	if (!window.Tabulator) {
		frappe.require([
			"https://unpkg.com/tabulator-tables@5.5.0/dist/css/tabulator_bootstrap4.min.css",
			"https://unpkg.com/tabulator-tables@5.5.0/dist/js/tabulator.min.js"
		], function() {
			init_page(page);
		});
	} else {
		init_page(page);
	}
};

function init_page(page) {
	page.body.html(get_review_center_shell());
	bind_review_center_events(page);
	load_review_center(page);
}

function get_review_center_shell() {
	return `
		<div class="abk-review-center">
			<div class="abk-review-tabs">
				<button class="active" data-tab="members">${__("Member Verification")} <span class="abk-badge-count bg-blue-500" data-summary="members">0</span></button>
				<button data-tab="submitted_info">${__("Submitted Info")} <span class="abk-badge-count bg-orange-500" data-summary="submitted_info">0</span></button>
				<button data-tab="experiences">${__("Parent Experiences")} <span class="abk-badge-count bg-purple-500" data-summary="experiences">0</span></button>
				<button data-tab="inquiries">${__("Parent Inquiries")} <span class="abk-badge-count bg-green-500" data-summary="inquiries">0</span></button>
			</div>
			<div class="abk-review-content">
				<section class="abk-review-section active" data-section="members"><div id="tabulator-members"></div></section>
				<section class="abk-review-section" data-section="submitted_info"><div id="tabulator-submitted_info"></div></section>
				<section class="abk-review-section" data-section="experiences"><div id="tabulator-experiences"></div></section>
				<section class="abk-review-section" data-section="inquiries"><div id="tabulator-inquiries"></div></section>
			</div>
		</div>
	`;
}

function bind_review_center_events(page) {
	page.body.on("click", ".abk-review-tabs button", function () {
		const tab = $(this).data("tab");
		page.body.find(".abk-review-tabs button").removeClass("active");
		$(this).addClass("active");
		page.body.find(".abk-review-section").removeClass("active");
		page.body.find(`.abk-review-section[data-section="${tab}"]`).addClass("active");
		
		// Trigger redraw if Tabulator is initialized to fix layout issues
		if (page.tables && page.tables[tab]) {
			page.tables[tab].redraw();
		}
	});

	page.body.on("click", ".abk-review-tabs button", function () {
		const tab = $(this).data("tab");
		page.body.find(".abk-review-tabs button").removeClass("active");
		$(this).addClass("active");
		page.body.find(".abk-review-section").removeClass("active");
		page.body.find(`.abk-review-section[data-section="${tab}"]`).addClass("active");
		
		// Trigger redraw if Tabulator is initialized to fix layout issues and reload data
		if (page.tables && page.tables[tab]) {
			page.tables[tab].redraw(true);
			page.tables[tab].setData();
		}
	});

	page.body.on("click", "[data-review-action]", function () {
		const button = $(this);
		const section = button.data("section");
		const action = button.data("review-action");
		const name = button.data("name");
		const label = button.text().trim();
		const run = () => run_review_action(page, section, action, name, label);

		if (action === "reject" || action === "close") {
			frappe.confirm(__("Are you sure you want to {0} this item?", [label.toLowerCase()]), run);
		} else {
			run();
		}
	});
}

function load_review_center(page) {
	frappe.call({
		method: "custom_special.abk_portal.page.abk_review_center.abk_review_center.get_review_center_data",
		callback(response) {
			const data = response.message || {};
			render_summary(page, data.summary || {});
			
			if (!page.tables) {
				page.tables = {};
				init_tabulator(page, "members", [
					{title: __("Name"), field: "full_name", headerFilter: "input"},
					{title: __("Phone"), field: "phone", headerFilter: "input"},
					{title: __("Relationship"), field: "relationship", formatter: cell => badge(cell.getValue(), "blue"), headerFilter: "input"},
					{title: __("City"), field: "city", headerFilter: "input"},
					{title: __("Created"), field: "creation", formatter: cell => format_date(cell.getValue())},
					{title: __("Actions"), formatter: cell => actions("members", cell.getData().name, [["verify", __("Verify"), "primary"], ["reject", __("Reject"), "danger"]])}
				], "ABK Member Profile");
				init_tabulator(page, "submitted_info", [
					{title: __("Place"), field: "place_name", headerFilter: "input"},
					{title: __("City"), field: "city", headerFilter: "input"},
					{title: __("Info Type"), field: "info_type", formatter: cell => badge(cell.getValue(), "orange"), headerFilter: "input"},
					{title: __("Submitter"), field: "submitter_name", headerFilter: "input"},
					{title: __("Created"), field: "creation", formatter: cell => format_date(cell.getValue())},
					{title: __("Actions"), formatter: cell => actions("submitted_info", cell.getData().name, [["approve", __("Approve"), "primary"], ["reject", __("Reject"), "danger"]])}
				], "User Submitted Info");
				init_tabulator(page, "experiences", [
					{title: __("Place"), field: "abk_place", headerFilter: "input"},
					{title: __("Reviewer"), field: "reviewer_name", headerFilter: "input"},
					{title: __("Relationship"), field: "reviewer_relationship", formatter: cell => badge(cell.getValue(), "blue"), headerFilter: "input"},
					{title: __("Title"), field: "experience_title", headerFilter: "input"},
					{title: __("Created"), field: "creation", formatter: cell => format_date(cell.getValue())},
					{title: __("Actions"), formatter: cell => actions("experiences", cell.getData().name, [["approve", __("Approve"), "primary"], ["reject", __("Reject"), "danger"]])}
				], "ABK Place Experience");
				init_tabulator(page, "inquiries", [
					{title: __("Parent"), field: "parent_name", headerFilter: "input"},
					{title: __("Phone"), field: "phone", headerFilter: "input"},
					{title: __("Inquiry Type"), field: "inquiry_type", formatter: cell => badge(cell.getValue(), "orange"), headerFilter: "input"},
					{title: __("City"), field: "city", headerFilter: "input"},
					{title: __("Status"), field: "status", formatter: cell => badge(cell.getValue(), cell.getValue() === "New" ? "red" : "blue"), headerFilter: "input"},
					{title: __("Created"), field: "creation", formatter: cell => format_date(cell.getValue())},
					{title: __("Actions"), formatter: cell => {
						const status = cell.getData().status;
						const acts = status === "New" ? 
							[["in_progress", __("In Progress"), "primary"], ["close", __("Close"), "secondary"]] : 
							[["contacted", __("Mark Contacted"), "primary"], ["close", __("Close"), "secondary"]];
						return actions("inquiries", cell.getData().name, acts);
					}}
				], "Parent Inquiry");
			} else {
				Object.values(page.tables).forEach(t => t.setData());
			}
		}
	});
}

function init_tabulator(page, section, columns, doctype) {
	page.tables[section] = new Tabulator(page.body.find(`#tabulator-${section}`)[0], {
		ajaxURL: "/api/method/custom_special.abk_portal.page.abk_review_center.abk_review_center.get_tabulator_data",
		ajaxParams: { section: section },
		ajaxConfig: {
			method: "GET",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
		},
		pagination: true,
		paginationMode: "remote",
		filterMode: "remote",
		sortMode: "remote",
		paginationSize: 20,
		layout: "fitColumns",
		columns: columns,
		ajaxResponse: function(url, params, response) {
			return response.message;
		}
	});

	page.tables[section].on("rowClick", function(e, row) {
		if ($(e.target).closest('button').length) return;
		open_detail_popup(doctype, row.getData().name);
	});
}

function open_detail_popup(doctype, name) {
	frappe.call({
		method: "frappe.client.get",
		args: { doctype: doctype, name: name },
		callback: function(r) {
			if(r && r.message) {
				const doc = r.message;
				let html = '<div class="table-responsive"><table class="table table-bordered table-hover"><tbody>';
				
				const ignore_fields = ['name', 'owner', 'creation', 'modified', 'modified_by', 'idx', 'docstatus', 'doctype', '_user_tags', '_comments', '_assign', '_liked_by'];
				
				for (let key in doc) {
					if(doc.hasOwnProperty(key) && !ignore_fields.includes(key) && typeof doc[key] !== 'object') {
						let val = doc[key] || '';
						if(val) {
							let display_val = frappe.utils.escape_html(String(val));
							if (typeof val === 'string' && val.startsWith('/files/') && val.match(/\.(jpeg|jpg|gif|png|webp|svg)$/i)) {
								display_val = `<a href="${val}" target="_blank"><img src="${val}" style="max-width: 100%; max-height: 250px; border-radius: 8px; margin-top: 8px; border: 1px solid #e5e7eb;"></a>`;
							}
							html += `<tr><td style="font-weight:bold; width: 35%;">${frappe.model.unscrub(key)}</td><td>${display_val}</td></tr>`;
						}
					}
				}
				html += '</tbody></table></div>';
				
				const d = new frappe.ui.Dialog({
					title: __("Detail") + ": " + name,
					size: "large",
					fields: [
						{
							fieldtype: "HTML",
							fieldname: "details",
							options: html
						}
					]
				});
				
				d.set_primary_action(__("Close"), function() {
					d.hide();
				});
				d.show();
			}
		}
	});
}

function run_review_action(page, section, action, name, label) {
	frappe.call({
		method: "custom_special.abk_portal.page.abk_review_center.abk_review_center.review_action",
		args: { section, action, name },
		freeze: true,
		freeze_message: __("Processing..."),
		callback() {
			frappe.show_alert({ message: __("{0} completed", [label]), indicator: "green" });
			load_review_center(page);
		},
	});
}

function render_summary(page, summary) {
	for (const [key, value] of Object.entries(summary)) {
		const badgeEl = page.body.find(`[data-summary="${key}"]`);
		badgeEl.text(value || 0);
		if(value > 0) {
			badgeEl.show();
		} else {
			badgeEl.hide();
		}
	}
}

function actions(section, name, items) {
	const action_buttons = items
		.map(([action, label, type]) => {
			const class_name = type === "danger" ? "btn-danger" : type === "primary" ? "btn-primary" : "btn-default";
			return `<button class="btn btn-xs ${class_name}" data-section="${section}" data-review-action="${action}" data-name="${escape_attr(name)}">${label}</button>`;
		})
		.join("");

	return `
		<div class="abk-actions">
			${action_buttons}
		</div>
	`;
}

function badge(value, colorCls) {
	if (!value) return "";
	return `<span class="indicator-pill ${colorCls}">${escape(value)}</span>`;
}

function format_date(value) {
	return value ? frappe.datetime.str_to_user(value) : "";
}

function escape(value) {
	return frappe.utils.escape_html(value || "");
}

function escape_attr(value) {
	return escape(value).replace(/"/g, "&quot;");
}
