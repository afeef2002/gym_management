# Copyright (c) 2026, Afeef Muhammed and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TrainerSession(Document):
    def validate(self):
        if not self.trainer:
            frappe.throw("Assign a trainer before publishing this session.")

        if (self.max_capacity or 0) < 1:
            frappe.throw("Session capacity must be at least one.")
