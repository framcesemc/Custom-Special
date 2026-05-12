(function () {
	let events_bound = false;

	function has_role(role) {
		return Array.isArray(frappe.user_roles) && frappe.user_roles.includes(role);
	}

	function can_run() {
		if (!window.frappe || !frappe.boot) {
			return false;
		}

		const boot_user = frappe.boot && frappe.boot.user;
		const user = typeof boot_user === "string" ? boot_user : boot_user && boot_user.name;

		return (
			user &&
			user !== "Guest" &&
			(window.location.pathname.startsWith("/app") || window.location.pathname.startsWith("/desk")) &&
			(has_role("System Manager") || has_role("ABK Admin"))
		);
	}

	function get_notification_button() {
		return $(".dropdown-notifications .nav-link, .notifications-icon").first();
	}

	function show_dot() {
		const button = get_notification_button();

		if (!button.length) {
			setTimeout(show_dot, 500);
			return;
		}

		button.addClass("abk-has-unread");

		if (!button.find(".abk-notification-dot").length) {
			button.append('<span class="abk-notification-dot" aria-hidden="true"></span>');
		}
	}

	function hide_dot() {
		const button = get_notification_button();
		button.removeClass("abk-has-unread");
		button.find(".abk-notification-dot").remove();
	}

	function refresh_frappe_notifications() {
		if (frappe.ui && frappe.ui.notifications) {
			if (typeof frappe.ui.notifications.get_notifications === "function") {
				frappe.ui.notifications.get_notifications();
			}
			if (typeof frappe.ui.notifications.get_notification_config === "function") {
				frappe.ui.notifications.get_notification_config();
			}
		}
	}

	function refresh_count() {
		if (!can_run()) {
			hide_dot();
			return;
		}

		frappe.call({
			method: "custom_special.abk_portal.notifications.get_unread_abk_notification_count",
			callback: function (response) {
				const count = cint(response.message || 0);

				if (count > 0) {
					show_dot();
				} else {
					hide_dot();
				}
			},
		});
	}

	function bind_events() {
		if (events_bound) {
			return;
		}

		events_bound = true;

		frappe.realtime.on("abk_admin_notification", function (data) {
			console.log("ABK realtime notification received:", data);

			if (!can_run() || !data) {
				return;
			}

			show_dot();
			refresh_frappe_notifications();

			frappe.show_alert(
				{
					message: frappe.utils.escape_html(
						data.subject || __("Info ABK baru menunggu review")
					),
					indicator: "orange",
				},
				8
			);
		});

		$(document).on("show.bs.dropdown", ".dropdown-notifications", function () {
			setTimeout(refresh_count, 700);
		});

		$(document).on("click", ".mark-as-read, [data-action='mark_all_as_read']", function () {
			setTimeout(refresh_count, 900);
		});

		if (frappe.router && typeof frappe.router.on === "function") {
			frappe.router.on("change", function () {
				setTimeout(refresh_count, 700);
			});
		}
	}

	function init() {
		if (!window.frappe || !frappe.boot) {
			setTimeout(init, 500);
			return;
		}

		bind_events();

		setTimeout(function () {
			if (can_run()) {
				refresh_count();
			}
		}, 1000);
	}

	$(init);
})();