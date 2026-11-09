import frappe
from frappe.utils import getdate, now_datetime, today


def get_context(context):
    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"
    context.logout_url = "/gym_logout"
    context.csrf_token = frappe.sessions.get_csrf_token()

    from gym_management.api import _get_linked_trainer

    trainer_name = _get_linked_trainer()

    context.trainer = frappe.get_doc("Trainer", trainer_name)
    now = now_datetime()
    today_date = getdate(today())
    context.sessions = frappe.get_all(
        "Trainer Session",
        filters={"trainer": trainer_name, "schedule_date_time": [">=", now]},
        fields=["name", "session_name", "description", "schedule_date_time", "max_capacity"],
        order_by="schedule_date_time asc",
        limit_page_length=100,
    )
    session_ids = [session.name for session in context.sessions]

    context.bookings = []
    context.confirmed_booking_count = 0
    context.today_session_count = sum(
        getdate(session.schedule_date_time) == today_date
        for session in context.sessions
    )

    if session_ids:
        booking_counts = {
            row.session: row.booking_count
            for row in frappe.get_all(
                "Session Booking",
                filters={
                    "session": ["in", session_ids],
                    "booking_status": "Confirmed",
                },
                fields=["session", "count(name) as booking_count"],
                group_by="session",
            )
        }
        context.bookings = frappe.get_all(
            "Session Booking",
            filters={
                "session": ["in", session_ids],
                "booking_status": "Confirmed",
            },
            fields=["name", "member", "session", "creation"],
            order_by="creation desc",
            limit_page_length=50,
        )
        member_ids = sorted({booking.member for booking in context.bookings if booking.member})
        members_by_id = {}
        if member_ids:
            members_by_id = {
                member.name: member.full_name
                for member in frappe.get_all(
                    "Gym Member",
                    filters={"name": ["in", member_ids]},
                    fields=["name", "full_name"],
                    limit_page_length=0,
                )
            }
        sessions_by_id = {session.name: session for session in context.sessions}
        for booking in context.bookings:
            session = sessions_by_id.get(booking.session)
            booking.member_name = members_by_id.get(booking.member, "Member unavailable")
            booking.session_name = session.session_name if session else "Session unavailable"
            booking.schedule_date_time = session.schedule_date_time if session else None

        context.confirmed_booking_count = sum(booking_counts.values())
        context.total_capacity = sum(session.max_capacity or 0 for session in context.sessions)
        context.filled_spots = min(context.confirmed_booking_count, context.total_capacity)
        context.available_spots = max(0, context.total_capacity - context.filled_spots)
    else:
        context.total_capacity = 0
        context.filled_spots = 0
        context.available_spots = 0
    for session in context.sessions:
        session.display_datetime = frappe.utils.format_datetime(session.schedule_date_time)
