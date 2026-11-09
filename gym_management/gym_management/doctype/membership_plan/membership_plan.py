# Copyright (c) 2026, Afeef Muhammed and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MembershipPlan(Document):
    def validate(self):
        if (self.duration_months or 0) < 1:
            frappe.throw("Membership plan duration must be at least one month.")

        if (self.regular_price or 0) < 0 or (self.student_price or 0) < 0:
            frappe.throw("Membership plan prices cannot be negative.")
