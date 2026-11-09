import frappe


def get_context(context):

    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"
    context.logout_url = "/gym_logout"
    context.bookings = []

    if not context.logged_in:
        return

    # Find the logged-in member
    member = frappe.db.get_value(
        "Gym Member",
        {"user": frappe.session.user},
        "name"
    )

    if not member:
        context.member_found = False
        return

    context.member_found = True

    # Retrieve only this member's bookings
    bookings = frappe.get_all(
        "Session Booking",
        filters={
            "member": member
        },
        fields=[
            "name",
            "session",
            "booking_status"
        ],
        order_by="creation desc"
    )

    # Retrieve session information
    for booking in bookings:

        session_details = frappe.db.get_value(
            "Trainer Session",
            booking.session,
            [
                "session_name",
                "trainer",
                "schedule_date_time"
            ],
            as_dict=True
        )

        booking.session_name = (
            session_details.session_name
            if session_details else "Session unavailable"
        )

        booking.trainer = (
            session_details.trainer
            if session_details else "Not available"
        )

        booking.schedule_date_time = (
            session_details.schedule_date_time
            if session_details else None
        )

    context.bookings = bookings