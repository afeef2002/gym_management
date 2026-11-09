import frappe


def get_context(context):
    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"
    context.logout_url = "/gym_logout"

    if "Gym Receptionist" not in frappe.get_roles():
        frappe.throw(
            "You do not have permission to view the receptionist dashboard.",
            frappe.PermissionError,
        )

    context.pending_count = frappe.db.count(
        "Gym Member",
        {"membership_status": "Pending Receptionist Review"},
    )
    context.pending_members = frappe.get_all(
        "Gym Member",
        filters={"membership_status": "Pending Receptionist Review"},
        fields=["name", "full_name", "email", "selected_plan", "creation"],
        order_by="creation asc",
        limit_page_length=0,
    )
