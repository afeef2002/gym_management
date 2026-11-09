import frappe
from datetime import datetime, time, timedelta
from frappe.utils import get_datetime, getdate, now_datetime, today


def _get_linked_trainer(user=None):
    user = user or frappe.session.user
    trainer_name = frappe.db.get_value("Trainer", {"user": user}, "name")
    if trainer_name:
        return trainer_name

    if "Gym Trainer" in frappe.get_roles(user):
        matching_profiles = frappe.get_all(
            "Trainer",
            filters={"email": user},
            pluck="name",
            limit_page_length=2,
        )
        if len(matching_profiles) == 1:
            return matching_profiles[0]

    frappe.throw(
        "Your account is not linked to a trainer profile. Ask the Gym Manager to link your user in the Trainer record.",
        frappe.PermissionError,
    )


def _require_trainer():
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to access the trainer calendar.", frappe.PermissionError)
    return _get_linked_trainer()


def _lock_trainer(trainer_name):
    trainer = frappe.qb.DocType("Trainer")
    (
        frappe.qb.from_(trainer)
        .select(trainer.name)
        .where(trainer.name == trainer_name)
        .for_update()
        .run()
    )


@frappe.whitelist()
def get_trainer_calendar(start_date, days=7):
    trainer_name = _require_trainer()
    start = getdate(start_date)
    days = frappe.utils.cint(days)
    if days < 1 or days > 14:
        frappe.throw("The calendar can display between one and fourteen days.")

    end = start + timedelta(days=days)
    sessions = frappe.get_all(
        "Trainer Session",
        filters={
            "trainer": trainer_name,
            "schedule_date_time": [
                "between",
                [datetime.combine(start, time.min), datetime.combine(end, time.min)],
            ],
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
        limit_page_length=500,
    )

    bookings_by_session = {}
    session_names = [session.name for session in sessions]
    if session_names:
        bookings = frappe.get_all(
            "Session Booking",
            filters={
                "session": ["in", session_names],
                "booking_status": "Confirmed",
            },
            fields=["session", "member"],
            limit_page_length=0,
        )
        member_ids = sorted({booking.member for booking in bookings if booking.member})
        member_names = {}
        if member_ids:
            member_names = {
                member.name: member.full_name
                for member in frappe.get_all(
                    "Gym Member",
                    filters={"name": ["in", member_ids]},
                    fields=["name", "full_name"],
                    limit_page_length=0,
                )
            }
        for booking in bookings:
            bookings_by_session.setdefault(booking.session, []).append(
                member_names.get(booking.member, "Member unavailable")
            )

    for session in sessions:
        scheduled_at = get_datetime(session.schedule_date_time)
        session.slot_date = scheduled_at.strftime("%Y-%m-%d")
        session.slot_hour = scheduled_at.hour
        session.schedule_date_time = scheduled_at.strftime("%Y-%m-%d %H:%M:%S")
        session.confirmed_members = bookings_by_session.get(session.name, [])
        session.booking_count = len(session.confirmed_members)

    return sessions


@frappe.whitelist()
def set_trainer_availability(slot_date, hour):
    trainer_name = _require_trainer()
    trainer_email = frappe.db.get_value("Trainer", trainer_name, "email")
    if not trainer_email:
        frappe.throw("Add a trainer email address before publishing availability.")
    frappe.utils.validate_email_address(trainer_email, throw=True)

    slot_date = getdate(slot_date)
    hour = frappe.utils.cint(hour)
    if hour < 0 or hour > 23:
        frappe.throw("Choose an hour from 00:00 to 23:00.")

    slot_datetime = datetime.combine(slot_date, time(hour=hour))
    if slot_datetime <= now_datetime():
        frappe.throw("Availability must be set for a future hour.")

    _lock_trainer(trainer_name)
    overlapping_sessions = frappe.get_all(
        "Trainer Session",
        filters={
            "trainer": trainer_name,
            "schedule_date_time": [
                "between",
                [
                    slot_datetime - timedelta(hours=1) + timedelta(seconds=1),
                    slot_datetime + timedelta(hours=1) - timedelta(seconds=1),
                ],
            ],
        },
        fields=["name"],
        limit_page_length=1,
    )
    if overlapping_sessions:
        frappe.throw("This hour overlaps an existing session or availability.")

    session = frappe.get_doc(
        {
            "doctype": "Trainer Session",
            "session_name": "Personal Training",
            "description": "One-hour trainer appointment.",
            "trainer": trainer_name,
            "schedule_date_time": slot_datetime,
            "max_capacity": 1,
            "is_trainer_availability": 1,
        }
    )
    session.insert(ignore_permissions=True)
    return {"name": session.name}


@frappe.whitelist()
def remove_trainer_availability(session_name):
    trainer_name = _require_trainer()
    _lock_trainer(trainer_name)

    trainer_session = frappe.qb.DocType("Trainer Session")
    (
        frappe.qb.from_(trainer_session)
        .select(trainer_session.name)
        .where(trainer_session.name == session_name)
        .for_update()
        .run()
    )
    session = frappe.get_doc("Trainer Session", session_name)
    if session.trainer != trainer_name or not session.is_trainer_availability:
        frappe.throw("You can only remove availability you created.", frappe.PermissionError)
    if frappe.db.exists(
        "Session Booking",
        {"session": session.name, "booking_status": "Confirmed"},
    ):
        frappe.throw("This hour is already booked and cannot be changed.")
    if session.schedule_date_time <= now_datetime():
        frappe.throw("Past availability cannot be changed.")

    frappe.delete_doc("Trainer Session", session.name, ignore_permissions=True)
    return {"success": True}


@frappe.whitelist()
def get_login_redirect():
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to continue.")

    roles = set(frappe.get_roles())
    if roles.intersection({"Gym Manager", "System Manager"}):
        return "/gym_manager_dashboard"

    is_linked_trainer = frappe.db.exists("Trainer", {"user": frappe.session.user})
    if "Gym Trainer" in roles or is_linked_trainer:
        return "/trainer_dashboard"

    return "/member"


@frappe.whitelist()
def book_session(session_name):
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to book a session.")

    member_name = frappe.db.get_value(
        "Gym Member",
        {"user": frappe.session.user},
        "name",
    )

    if not member_name:
        frappe.throw("Your gym member profile was not found.")

    member = frappe.get_doc("Gym Member", member_name)

    if member.membership_status != "Active":
        frappe.throw("Only active members can book sessions.")

    if member.membership_end_date and getdate(member.membership_end_date) < getdate(today()):
        frappe.throw("Your membership has expired. Please contact the gym.")

    if not session_name:
        frappe.throw("Please select a session.")

    # Serialize bookings for a session so simultaneous requests cannot exceed its capacity.
    trainer_session = frappe.qb.DocType("Trainer Session")
    (
        frappe.qb.from_(trainer_session)
        .select(trainer_session.name)
        .where(trainer_session.name == session_name)
        .for_update()
        .run()
    )
    session = frappe.get_doc("Trainer Session", session_name)

    if session.schedule_date_time < now_datetime():
        frappe.throw("This session has already started or passed.")

    if not session.trainer:
        frappe.throw("This session does not have an assigned trainer and cannot be booked.")

    trainer_email = frappe.db.get_value("Trainer", session.trainer, "email")
    if not trainer_email:
        frappe.throw("The assigned trainer does not have an email address; this session cannot be booked.")
    frappe.utils.validate_email_address(trainer_email, throw=True)

    booking_doctype = frappe.qb.DocType("Session Booking")
    confirmed_bookings = (
        frappe.qb.from_(booking_doctype)
        .select(booking_doctype.name, booking_doctype.member)
        .where(booking_doctype.session == session.name)
        .where(booking_doctype.booking_status == "Confirmed")
        .for_update()
        .run(as_dict=True)
    )

    if any(booking.member == member.name for booking in confirmed_bookings):
        frappe.throw("You have already booked this session.")

    booked_count = len(confirmed_bookings)

    if booked_count >= (session.max_capacity or 0):
        frappe.throw("Sorry, this session is full.")

    booking = frappe.get_doc({
        "doctype": "Session Booking",
        "member": member.name,
        "session": session.name,
        "booking_status": "Confirmed"
    })

    booking.insert(ignore_permissions=True)

    frappe.sendmail(
        recipients=[trainer_email],
        subject=f"New booking for {session.session_name}",
        message=(
            f"{frappe.utils.escape_html(member.full_name)} booked "
            f"{frappe.utils.escape_html(session.session_name)} "
            f"({frappe.utils.format_datetime(session.schedule_date_time)}). "
            f"Member email: {frappe.utils.escape_html(member.email)}"
        ),
        reference_doctype="Session Booking",
        reference_name=booking.name,
    )

    return {
        "message": "Session booked successfully!"
    }


@frappe.whitelist(allow_guest=True)
def register_member(
    full_name,
    email,
    phone,
    customer_type,
    selected_plan,
    password,
    confirm_password
):
    # Clean and validate submitted information
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    phone = (phone or "").strip()
    password = password or ""
    confirm_password = confirm_password or ""

    if not all([
        full_name,
        email,
        phone,
        customer_type,
        selected_plan,
        password,
        confirm_password
    ]):
        frappe.throw("Please fill in all required fields.")

    frappe.utils.validate_email_address(email, throw=True)

    if customer_type not in ["Student", "Regular"]:
        frappe.throw("Please select a valid customer type.")

    if not frappe.db.exists("Membership Plan", selected_plan):
        frappe.throw("Please select a valid membership plan.")

    if len(password) < 8:
        frappe.throw("Your password must contain at least 8 characters.")

    if password != confirm_password:
        frappe.throw("The passwords do not match.")

    # Prevent duplicate member registrations and user accounts
    if frappe.db.exists("Gym Member", {"email": email}):
        frappe.throw("A member registration already exists with this email.")

    if frappe.db.exists("User", email):
        frappe.throw("An account with this email already exists. Please log in.")

    # Create the Frappe login account
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name,
        "enabled": 1,
        "user_type": "Website User",
        "send_welcome_email": 0,
        "new_password": password
    })

    if not frappe.db.exists("Role", "Gym Member User"):
        frappe.throw("The Gym Member User role is not configured. Please contact the gym.")

    user.append("roles", {"role": "Gym Member User"})

    user.insert(ignore_permissions=True)

    # Create the Gym Member profile and link it to the new account
    member = frappe.get_doc({
        "doctype": "Gym Member",
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "customer_type": customer_type,
        "selected_plan": selected_plan,
        "membership_status": "Pending Receptionist Review",
        "user": user.name,
        "owner": user.name,
    })

    member.insert(ignore_permissions=True)
    frappe.db.set_value(
        "Gym Member",
        member.name,
        "owner",
        user.name,
        update_modified=False,
    )

    return {
        "success": True,
        "message": (
            "Registration successful! Your login account has been created. "
            "Your registration is awaiting receptionist verification. You can log in, but "
            "membership features will be available after approval."
        )
    }
