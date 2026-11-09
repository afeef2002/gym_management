import frappe

def get_context(context):

    context.no_cache = 1

    if frappe.session.user == "Guest":
        context.logged_in = False
        return

    context.logged_in = True
    context.logout_url = "/gym_logout"

    members = frappe.get_list(
        "Gym Member",
        filters={
            "user": frappe.session.user
        },
        fields=[
            "name",
            "full_name",
            "email",
            "phone",
            "customer_type",
            "membership_status",
            "selected_plan",
            "membership_price",
            "membership_start_date",
            "membership_end_date",
            "payment_status"
        ],
        limit_page_length=1
    )

    context.member = members[0] if members else None