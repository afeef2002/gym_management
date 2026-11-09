# Copyright (c) 2026, Afeef Muhammed and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, getdate, today


class GymMember(Document):
    def before_insert(self):
        self.set_membership_price()

    def validate(self):
        self.update_membership_price_if_plan_changed()
        if not self.selected_plan or not self.customer_type:
            frappe.throw("A membership plan and customer type are required.")
        self.validate_payment_amount()
        self.set_payment_status()
        self.set_payment_date()
        self.set_membership_dates_on_activation()

    def on_update(self):
        previous = self.get_doc_before_save()
        if self.assigned_trainer and (
            not previous or previous.assigned_trainer != self.assigned_trainer
        ):
            self.notify_assigned_trainer()

    def notify_assigned_trainer(self):
        trainer = frappe.get_value(
            "Trainer",
            self.assigned_trainer,
            ["trainer_name", "email"],
            as_dict=True,
        )
        if not trainer or not trainer.email:
            frappe.throw("The assigned trainer must have an email address to receive notifications.")
        frappe.utils.validate_email_address(trainer.email, throw=True)

        message = (
            f"<p>Hello {frappe.utils.escape_html(trainer.trainer_name)},</p>"
            f"<p>You have been assigned a new gym member.</p>"
            "<ul>"
            f"<li><strong>Member:</strong> {frappe.utils.escape_html(self.full_name)}</li>"
            f"<li><strong>Email:</strong> {frappe.utils.escape_html(self.email or '')}</li>"
            f"<li><strong>Phone:</strong> {frappe.utils.escape_html(self.phone or '')}</li>"
            f"<li><strong>Membership plan:</strong> {frappe.utils.escape_html(self.selected_plan or '')}</li>"
            "</ul>"
        )
        frappe.sendmail(
            recipients=[trainer.email],
            subject=f"New member assigned: {self.full_name}",
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name,
        )

    def set_membership_price(self):
        if not self.selected_plan or not self.customer_type:
            return

        prices = frappe.db.get_value(
            "Membership Plan",
            self.selected_plan,
            ["regular_price", "student_price"],
            as_dict=True,
        )
        if not prices:
            frappe.throw("Please select a valid membership plan.")

        price_field = "student_price" if self.customer_type == "Student" else "regular_price"
        price = prices.get(price_field)
        if price is None:
            frappe.throw("The selected membership plan has no price for this customer type.")

        self.membership_price = price

    def update_membership_price_if_plan_changed(self):
        previous = self.get_doc_before_save()
        if not previous or (
            previous.selected_plan != self.selected_plan
            or previous.customer_type != self.customer_type
        ):
            self.set_membership_price()

    def validate_payment_amount(self):
        amount_paid = self.amount_paid or 0
        membership_price = self.membership_price or 0
        if amount_paid < 0 or amount_paid > membership_price:
            frappe.throw("Amount paid must be between zero and the membership price.")

    def set_payment_status(self):
        amount_paid = self.amount_paid or 0
        membership_price = self.membership_price or 0
        if membership_price == 0:
            self.payment_status = "Paid"
        elif amount_paid == 0:
            self.payment_status = "Unpaid"
        elif amount_paid < membership_price:
            self.payment_status = "Partially Paid"
        else:
            self.payment_status = "Paid"

    def set_payment_date(self):
        previous = self.get_doc_before_save()
        amount_changed = not previous or previous.amount_paid != self.amount_paid
        if self.amount_paid and amount_changed and not self.payment_date:
            self.payment_date = today()

    def set_membership_dates_on_activation(self):
        previous = self.get_doc_before_save()
        was_active = previous and previous.membership_status == "Active"
        if self.membership_status != "Active" or was_active:
            return

        if not self.membership_start_date:
            self.membership_start_date = today()

        if not self.membership_end_date:
            duration = frappe.db.get_value(
                "Membership Plan",
                self.selected_plan,
                "duration_months",
            ) or 1
            self.membership_end_date = add_months(getdate(self.membership_start_date), duration)
