import frappe
from frappe.utils import getdate, now_datetime, today


def get_context(context):
    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"
    context.logout_url = "/gym_logout"

    roles = set(frappe.get_roles())
    if not roles.intersection({"Gym Manager", "System Manager"}):
        frappe.throw("You do not have permission to view the manager dashboard.", frappe.PermissionError)

    today_date = getdate(today())
    now = now_datetime()
    context.member_count = frappe.db.count("Gym Member")
    context.pending_count = frappe.db.count(
        "Gym Member",
        {"membership_status": ["in", ["Pending Receptionist Review", "Pending Manager Approval"]]},
    )
    nominal_active_count = frappe.db.count("Gym Member", {"membership_status": "Active"})
    past_end_date_count = frappe.db.count(
        "Gym Member",
        {"membership_status": "Active", "membership_end_date": ["<", today_date]},
    )
    context.active_count = nominal_active_count - past_end_date_count
    context.expired_count = frappe.db.count("Gym Member", {"membership_status": "Expired"}) + past_end_date_count
    context.pending_members = frappe.get_all(
        "Gym Member",
        filters={
            "membership_status": ["in", ["Pending Receptionist Review", "Pending Manager Approval"]]
        },
        fields=["name", "full_name", "email", "membership_status", "creation"],
        order_by="creation desc",
        limit_page_length=8,
    )

    context.upcoming_sessions = frappe.get_all(
        "Trainer Session",
        filters={"schedule_date_time": [">=", now]},
        fields=["name", "session_name", "trainer", "schedule_date_time", "max_capacity"],
        order_by="schedule_date_time asc",
        limit_page_length=8,
    )
    today_sessions = frappe.get_all(
        "Trainer Session",
        filters={
            "schedule_date_time": [
                "between",
                [f"{today_date} 00:00:00", f"{today_date} 23:59:59"],
            ]
        },
        fields=["name"],
        limit_page_length=0,
    )
    today_session_ids = [session.name for session in today_sessions]
    context.today_session_count = len(today_session_ids)
    context.today_booking_count = (
        frappe.db.count(
            "Session Booking",
            {"session": ["in", today_session_ids], "booking_status": "Confirmed"},
        )
        if today_session_ids
        else 0
    )
    trainer_names = sorted({session.trainer for session in context.upcoming_sessions if session.trainer})
    trainers_by_id = {}
    if trainer_names:
        trainers_by_id = {
            trainer.name: trainer.trainer_name
            for trainer in frappe.get_all(
                "Trainer",
                filters={"name": ["in", trainer_names]},
                fields=["name", "trainer_name"],
                limit_page_length=0,
            )
        }
    for session in context.upcoming_sessions:
        session.trainer_name = trainers_by_id.get(session.trainer, "Not assigned")
        session.display_datetime = frappe.utils.format_datetime(session.schedule_date_time)

    context.today_attendance_count = frappe.db.count(
        "Member Attendance Log",
        {"date": today_date},
    )
