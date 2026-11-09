import frappe

def get_context(context):
    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"

    context.plans = frappe.get_all(
        "Membership Plan",
        fields=[
            "name",
            "plan_name",
            "regular_price",
            "student_price",
            "description"
        ],
        order_by="plan_name asc"
    )