# Copyright (c) 2026, Afeef Muhammed and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, now_datetime, today

from gym_management.api import (
    get_login_redirect,
    get_trainer_calendar,
    remove_trainer_availability,
    set_trainer_availability,
)
from gym_management.www.book_sessions import get_context as get_booking_context
from gym_management.www.gym_manager_dashboard import get_context as get_manager_dashboard_context
from gym_management.www.trainer_dashboard import get_context as get_trainer_dashboard_context


class TestTrainer(FrappeTestCase):
    def test_booking_filter_lists_trainers_without_scheduled_sessions(self):
        trainer = frappe.get_doc(
            {
                "doctype": "Trainer",
                "trainer_name": "Unscheduled Filter Test Trainer",
                "email": "unscheduled-trainer@example.com",
            }
        ).insert(ignore_permissions=True)

        context = frappe._dict()
        get_booking_context(context)

        self.assertTrue(context.csrf_token)
        self.assertIn(trainer.name, {row.name for row in context.trainers})

    def test_trainer_dashboard_shows_only_linked_trainers_sessions(self):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "gym-trainer-dashboard-test@example.com",
                "first_name": "Trainer Dashboard Test",
                "user_type": "Website User",
                "enabled": 1,
                "send_welcome_email": 0,
            }
        )
        user.insert(ignore_permissions=True)

        trainer = frappe.get_doc(
            {
                "doctype": "Trainer",
                "trainer_name": "Dashboard Test Trainer",
                "email": user.name,
                "user": user.name,
            }
        ).insert(ignore_permissions=True)
        session = frappe.get_doc(
            {
                "doctype": "Trainer Session",
                "session_name": "Dashboard Test Session",
                "trainer": trainer.name,
                "schedule_date_time": add_to_date(now_datetime(), days=2, as_datetime=True),
                "max_capacity": 5,
            }
        ).insert(ignore_permissions=True)
        other_trainer = frappe.get_doc(
            {
                "doctype": "Trainer",
                "trainer_name": "Other Dashboard Trainer",
                "email": "other-dashboard-trainer@example.com",
            }
        ).insert(ignore_permissions=True)
        other_session = frappe.get_doc(
            {
                "doctype": "Trainer Session",
                "session_name": "Other Dashboard Session",
                "trainer": other_trainer.name,
                "schedule_date_time": add_to_date(now_datetime(), days=3, as_datetime=True),
                "max_capacity": 5,
            }
        ).insert(ignore_permissions=True)

        try:
            frappe.set_user(user.name)
            context = frappe._dict()
            get_trainer_dashboard_context(context)
            rendered_page = frappe.get_template("www/trainer_dashboard.html").render(context)
            login_redirect = get_login_redirect()
        finally:
            frappe.set_user("Administrator")

        self.assertEqual(context.trainer.name, trainer.name)
        self.assertIn(session.name, {row.name for row in context.sessions})
        self.assertNotIn(other_session.name, {row.name for row in context.sessions})
        self.assertIn("Welcome, Dashboard Test Trainer.", rendered_page)
        self.assertIn("My Calendar", rendered_page)
        self.assertNotIn("My Bookings", rendered_page)
        self.assertIn('id="trainer-calendar"', rendered_page)
        self.assertIn('id="calendar-hours"', rendered_page)
        self.assertIn(f'data-csrf-token="{context.csrf_token}"', rendered_page)
        self.assertEqual(login_redirect, "/trainer_dashboard")

    def test_trainer_dashboard_rejects_accounts_without_trainer_profile(self):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "unlinked-trainer-dashboard-test@example.com",
                "first_name": "Unlinked Trainer Test",
                "user_type": "Website User",
                "enabled": 1,
                "send_welcome_email": 0,
            }
        )
        user.append("roles", {"role": "Gym Trainer"})
        user.insert(ignore_permissions=True)

        try:
            frappe.set_user(user.name)
            with self.assertRaises(frappe.PermissionError):
                get_trainer_dashboard_context(frappe._dict())
        finally:
            frappe.set_user("Administrator")

    def test_manager_dashboard_loads_gym_overview(self):
        context = frappe._dict()

        get_manager_dashboard_context(context)
        rendered_page = frappe.get_template("www/gym_manager_dashboard.html").render(context)

        self.assertGreaterEqual(context.member_count, 0)
        self.assertGreaterEqual(context.today_session_count, 0)
        self.assertIn("Manager dashboard", rendered_page)

    def test_trainer_can_publish_and_remove_one_hour_availability(self):
        user, trainer = self.create_linked_trainer("calendar-availability")
        slot_date = add_days(today(), 2)

        try:
            frappe.set_user(user.name)
            result = set_trainer_availability(slot_date, 15)
            sessions = get_trainer_calendar(slot_date, 1)
            created = next(session for session in sessions if session.name == result["name"])

            self.assertEqual(created.slot_hour, 15)
            self.assertEqual(created.max_capacity, 1)
            self.assertEqual(created.trainer, trainer.name)
            with self.assertRaises(frappe.ValidationError):
                set_trainer_availability(slot_date, 15)

            remove_trainer_availability(result["name"])
            self.assertFalse(frappe.db.exists("Trainer Session", result["name"]))
        finally:
            frappe.set_user("Administrator")

    def test_booked_availability_cannot_be_removed_and_is_hidden_from_members(self):
        user, _trainer = self.create_linked_trainer("calendar-booked")
        plan = frappe.get_doc(
            {
                "doctype": "Membership Plan",
                "plan_name": "Gym Only",
                "regular_price": 120,
                "student_price": 80,
            }
        ).insert(ignore_permissions=True)
        member = frappe.get_doc(
            {
                "doctype": "Gym Member",
                "full_name": "Calendar Booking Member",
                "email": "calendar-booked-member@example.com",
                "customer_type": "Regular",
                "selected_plan": plan.name,
                "membership_status": "Pending Receptionist Review",
                "user": "Administrator",
            }
        ).insert(ignore_permissions=True)
        slot_date = add_days(today(), 3)

        try:
            frappe.set_user(user.name)
            session_name = set_trainer_availability(slot_date, 11)["name"]
        finally:
            frappe.set_user("Administrator")

        frappe.get_doc(
            {
                "doctype": "Session Booking",
                "member": member.name,
                "session": session_name,
                "booking_status": "Confirmed",
            }
        ).insert(ignore_permissions=True)

        try:
            frappe.set_user(user.name)
            with self.assertRaises(frappe.ValidationError):
                remove_trainer_availability(session_name)
        finally:
            frappe.set_user("Administrator")

        context = frappe._dict()
        get_booking_context(context)
        self.assertNotIn(session_name, {session.name for session in context.sessions})

    def create_linked_trainer(self, suffix):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"gym-trainer-{suffix}@example.com",
                "first_name": "Calendar Trainer",
                "user_type": "Website User",
                "enabled": 1,
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
        trainer = frappe.get_doc(
            {
                "doctype": "Trainer",
                "trainer_name": f"Calendar Trainer {suffix}",
                "email": user.name,
                "user": user.name,
            }
        ).insert(ignore_permissions=True)
        return user, trainer
