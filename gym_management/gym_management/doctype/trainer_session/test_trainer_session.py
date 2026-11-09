# Copyright (c) 2026, Afeef Muhammed and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTrainerSession(FrappeTestCase):
    def test_trainer_is_required_for_scheduled_session(self):
        session = frappe.new_doc("Trainer Session")

        with self.assertRaises(frappe.ValidationError):
            session.validate()
