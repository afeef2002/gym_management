# Copyright (c) 2026, Afeef Muhammed and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase

from gym_management.api import register_member


class TestGymMember(FrappeTestCase):
    def test_assigned_trainer_is_notified_on_member_registration_and_assignment(self):
        plan = frappe.get_doc(
            {
                "doctype": "Membership Plan",
                "plan_name": "Gym Only",
                "regular_price": 120,
                "student_price": 80,
            }
        ).insert(ignore_permissions=True)
        trainer = frappe.get_doc(
            {
                "doctype": "Trainer",
                "trainer_name": "Assigned Member Trainer",
                "email": "assigned-member-trainer@example.com",
            }
        ).insert(ignore_permissions=True)

        member = frappe.get_doc(
            {
                "doctype": "Gym Member",
                "full_name": "Assigned Member Registration",
                "email": "assigned-member@example.com",
                "phone": "5550100",
                "customer_type": "Regular",
                "selected_plan": plan.name,
                "membership_status": "Pending Receptionist Review",
                "assigned_trainer": trainer.name,
            }
        )

        with patch("frappe.sendmail") as sendmail:
            member.insert(ignore_permissions=True)

        sendmail.assert_called_once()
        email = sendmail.call_args.kwargs
        self.assertEqual(email["recipients"], [trainer.email])
        self.assertEqual(email["reference_name"], member.name)
        self.assertIn(member.full_name, email["subject"])

    def test_assigning_trainer_after_member_registration_sends_one_notification(self):
        plan = frappe.get_doc(
            {
                "doctype": "Membership Plan",
                "plan_name": "Zumba",
                "regular_price": 100,
                "student_price": 75,
            }
        ).insert(ignore_permissions=True)
        trainer = frappe.get_doc(
            {
                "doctype": "Trainer",
                "trainer_name": "Later Assigned Trainer",
                "email": "later-assigned-trainer@example.com",
            }
        ).insert(ignore_permissions=True)
        member = frappe.get_doc(
            {
                "doctype": "Gym Member",
                "full_name": "Member Assigned Later",
                "email": "member-assigned-later@example.com",
                "customer_type": "Regular",
                "selected_plan": plan.name,
                "membership_status": "Pending Receptionist Review",
            }
        ).insert(ignore_permissions=True)

        with patch("frappe.sendmail") as sendmail:
            member.assigned_trainer = trainer.name
            member.save(ignore_permissions=True)
            member.full_name = "Member Details Updated"
            member.save(ignore_permissions=True)

        sendmail.assert_called_once()

    def test_student_price_is_snapshotted_and_payment_status_is_derived(self):
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
                "full_name": "Test Gym Member",
                "email": "gym-member-test@example.com",
                "customer_type": "Student",
                "selected_plan": plan.name,
                "membership_status": "Pending Receptionist Review",
                "amount_paid": 20,
            }
        )
        member.before_insert()
        member.validate()

        self.assertEqual(member.membership_price, 80)
        self.assertEqual(member.payment_status, "Partially Paid")

    def test_registration_creates_member_owned_by_the_website_user(self):
        plan = frappe.get_doc(
            {
                "doctype": "Membership Plan",
                "plan_name": "Zumba",
                "regular_price": 100,
                "student_price": 75,
                "duration_months": 1,
            }
        ).insert(ignore_permissions=True)

        try:
            frappe.set_user("Guest")
            register_member(
                full_name="Registration Test Member",
                email="gym-registration-test@example.com",
                phone="5550100",
                customer_type="Regular",
                selected_plan=plan.name,
                password="Stronger-pass-123!",
                confirm_password="Stronger-pass-123!",
            )
        finally:
            frappe.set_user("Administrator")

        member_name = frappe.db.get_value(
            "Gym Member",
            {"email": "gym-registration-test@example.com"},
            "name",
        )
        member = frappe.get_doc("Gym Member", member_name)
        self.assertEqual(member.membership_status, "Pending Receptionist Review")
        self.assertEqual(member.owner, "gym-registration-test@example.com")
        self.assertEqual(member.membership_price, 100)

    def test_receptionist_and_manager_complete_member_workflow(self):
        plan = frappe.get_doc(
            {
                "doctype": "Membership Plan",
                "plan_name": "All-in-One",
                "regular_price": 150,
                "student_price": 110,
                "duration_months": 3,
            }
        ).insert(ignore_permissions=True)
        member = frappe.get_doc(
            {
                "doctype": "Gym Member",
                "full_name": "Workflow Test Member",
                "email": "gym-workflow-member@example.com",
                "customer_type": "Regular",
                "selected_plan": plan.name,
                "membership_status": "Pending Receptionist Review",
            }
        ).insert(ignore_permissions=True)

        receptionist = self.create_staff_user(
            "gym-workflow-receptionist@example.com",
            "Gym Receptionist",
        )
        manager = self.create_staff_user(
            "gym-workflow-manager@example.com",
            "Gym Manager",
        )

        try:
            frappe.set_user(receptionist.name)
            apply_workflow({"doctype": "Gym Member", "name": member.name}, "Send to Manager")

            frappe.set_user(manager.name)
            apply_workflow({"doctype": "Gym Member", "name": member.name}, "Activate Membership")
        finally:
            frappe.set_user("Administrator")

        member.reload()
        self.assertEqual(member.membership_status, "Active")
        self.assertIsNotNone(member.membership_start_date)
        self.assertIsNotNone(member.membership_end_date)

    def create_staff_user(self, email, role):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Workflow Test",
                "user_type": "System User",
                "enabled": 1,
                "send_welcome_email": 0,
            }
        )
        user.append("roles", {"role": role})
        return user.insert(ignore_permissions=True)
