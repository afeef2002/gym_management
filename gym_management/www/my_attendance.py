import frappe

def get_context(context):
    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"
    context.logout_url = "/gym_logout"
    context.member_found = False
    context.attendance = []

    if not context.logged_in:
        return

    # Find the Gym Member record linked to the logged-in user
    member = frappe.db.get_value(
        "Gym Member",
        {"user": frappe.session.user},
        "name"
    )

    if not member:
        return

    context.member_found = True

    # Retrieve only this member's attendance records
    context.attendance = frappe.get_all(
        "Member Attendance Log",
        filters={"member": member},
        fields=[
            "name",
            "date",
            "check_in_time",
            "workout_notes"
        ],
        order_by="date desc",
        limit_page_length=500
    )