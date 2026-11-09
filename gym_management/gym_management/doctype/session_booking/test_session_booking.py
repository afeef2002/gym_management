# Copyright (c) 2026, Afeef Muhammed and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime
from frappe.tests.utils import FrappeTestCase

from gym_management.api import book_session


class TestSessionBooking(FrappeTestCase):
    def test_booking_notifies_trainer_and_prevents_duplicates(self):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "gym-booking-test@example.com",
                "first_name": "Booking Test",
                "user_type": "Website User",
                "enabled": 1,
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
        plan = frappe.get_doc(
            {
                "doctype": "Membership Plan",
                "plan_name": "Gym Only",
                "regular_price": 120,
                "student_price": 80,
                "duration_months": 1,
            }
        ).insert(ignore_permissions=True)
        member = frappe.get_doc(
            {
                "doctype": "Gym Member",
                "full_name": "Booking Test Member",
                "email": user.name,
                "customer_type": "Regular",
                "selected_plan": plan.name,
                "membership_status": "Pending Receptionist Review",
                "user": user.name,
                "owner": user.name,
            }
        ).insert(ignore_permissions=True)
        frappe.db.set_value("Gym Member", member.name, "membership_status", "Active")

        trainer = frappe.get_doc(
            {
                "doctype": "Trainer",
                "trainer_name": "Booking Test Trainer",
                "email": "gym-trainer-test@example.com",
            }
        ).insert(ignore_permissions=True)
        session = frappe.get_doc(
            {
                "doctype": "Trainer Session",
                "session_name": "Booking Test Session",
                "trainer": trainer.name,
                "schedule_date_time": add_to_date(now_datetime(), days=1, as_datetime=True),
                "max_capacity": 1,
            }
        ).insert(ignore_permissions=True)

        try:
            frappe.set_user(user.name)
            with patch("frappe.sendmail") as sendmail:
                self.assertIn("successfully", book_session(session.name)["message"])
                sendmail.assert_called_once()
                with self.assertRaises(frappe.ValidationError):
                    book_session(session.name)
        finally:
            frappe.set_user("Administrator")
