import frappe
from frappe.utils import getdate, now_datetime


def get_context(context):
    context.no_cache = 1

    context.logged_in = frappe.session.user != "Guest"
    context.logout_url = "/gym_logout"
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.today = getdate(now_datetime()).isoformat()
    context.sessions = []
    context.member_status = None
    context.can_book = False

    context.sessions = frappe.get_all(
        "Trainer Session",
        filters={
            "schedule_date_time": [">=", now_datetime()]
        },
        fields=[
            "name",
            "session_name",
            "trainer",
            "description",
            "schedule_date_time",
            "max_capacity",
            "is_trainer_availability",
        ],
        order_by="schedule_date_time asc",
        limit_page_length=500
    )

    trainers_by_id = {
        trainer.name: trainer
        for trainer in frappe.get_all(
            "Trainer",
            fields=["name", "trainer_name", "specialization", "email"],
            order_by="trainer_name asc",
            limit_page_length=0,
        )
    }

    context.trainers = sorted(
        trainers_by_id.values(),
        key=lambda trainer: (trainer.trainer_name or "").casefold(),
    )

    booked_counts = {}
    if context.sessions:
        booked_counts = {
            booking.session: booking.booked_count
            for booking in frappe.get_all(
                "Session Booking",
                filters={
                    "session": ["in", [session.name for session in context.sessions]],
                    "booking_status": "Confirmed",
                },
                fields=["session", "count(name) as booked_count"],
                group_by="session",
            )
        }

    if context.logged_in:
        member_name = frappe.db.get_value(
            "Gym Member",
            {"user": frappe.session.user},
            "name"
        )
        if member_name:
            context.member_status = frappe.db.get_value(
                "Gym Member",
                member_name,
                "membership_status"
            )
            context.can_book = context.member_status == "Active"

    for session in context.sessions:
        trainer = trainers_by_id.get(session.trainer)
        session.trainer_name = trainer.trainer_name if trainer else None
        session.trainer_specialization = trainer.specialization if trainer else None
        session.trainer_email_available = bool(trainer and trainer.email)
        session.session_date = getdate(session.schedule_date_time).isoformat()
        session.session_weekday = getdate(session.schedule_date_time).strftime("%a")
        session.session_day = getdate(session.schedule_date_time).strftime("%d")
        session.session_month = getdate(session.schedule_date_time).strftime("%b")
        session.session_time = frappe.utils.format_datetime(
            session.schedule_date_time,
            "h:mm a",
        )
        session.booked_count = booked_counts.get(session.name, 0)

        session.available_seats = max(
            0,
            (session.max_capacity or 0) - session.booked_count
        )
        session.capacity_percent = round(
            session.available_seats / session.max_capacity * 100
        ) if session.max_capacity else 0

    context.sessions = [
        session
        for session in context.sessions
        if not (session.is_trainer_availability and session.available_seats == 0)
    ]