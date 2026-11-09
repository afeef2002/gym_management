import frappe

def get_context(context):
    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"

    # Generate a CSRF token for this visitor's session
    context.csrf_token = frappe.sessions.get_csrf_token()

    # Load membership plans for the registration form
    context.plans = frappe.get_all(
        "Membership Plan",
        fields=["name", "plan_name"],
        order_by="plan_name asc"
    )