# Copyright (c) 2026, Afeef Muhammed and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Trainer(Document):
    def validate(self):
        if self.user and frappe.db.exists(
            "Trainer",
            {"user": self.user, "name": ["!=", self.name]},
        ):
            frappe.throw("This user is already linked to another trainer profile.")
