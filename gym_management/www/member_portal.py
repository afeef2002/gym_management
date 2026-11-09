import frappe
from frappe.utils import now_datetime


def get_context(context):

    context.no_cache = 1

    if frappe.session.user == "Guest":
        frappe.throw("Please log in to access the Gym Member Portal.")

    context.logged_in = True
    context.logout_url = "/gym_logout"

    member_name = frappe.db.get_value(
        "Gym Member",
        {"user": frappe.session.user},
        "name"
    )

    if not member_name:
        frappe.throw(
            "Your account is not linked to a Gym Member record."
        )

    context.member = frappe.get_doc(
        "Gym Member",
        member_name
    )

    context.sessions = frappe.get_all(
        "Trainer Session",
        filters={
            "schedule_date_time": [">=", now_datetime()]
        },
        fields=[
            "name",
            "session_name",
            "schedule_date_time",
            "trainer"
        ],
        order_by="schedule_date_time asc",
        limit_page_length=50
    )

    context.plan_name = frappe.db.get_value(
        "Membership Plan",
        context.member.selected_plan,
        "plan_name"
    )

    return context
