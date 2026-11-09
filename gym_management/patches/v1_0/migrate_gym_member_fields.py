import frappe


def execute():
    if frappe.db.has_column("Member Attendance Log", "workout_notesprogress"):
        frappe.db.sql(
            """
            UPDATE `tabMember Attendance Log`
            SET workout_notes = workout_notesprogress
            WHERE IFNULL(workout_notes, '') = ''
              AND IFNULL(workout_notesprogress, '') != ''
            """
        )

    if frappe.db.has_column("Gym Member", "membership_status"):
        frappe.db.sql(
            """
            UPDATE `tabGym Member`
            SET membership_status = 'Pending Receptionist Review'
            WHERE membership_status = 'Pending Approval'
            """
        )
        frappe.db.sql(
            """
            UPDATE `tabGym Member`
            SET owner = user
            WHERE IFNULL(user, '') != '' AND owner != user
            """
        )

    frappe.db.sql(
        """
        UPDATE `tabMembership Plan`
        SET duration_months = 1
        WHERE IFNULL(duration_months, 0) < 1
        """
    )
    frappe.db.sql(
        """
        UPDATE `tabMembership Plan`
        SET regular_price = 0
        WHERE regular_price IS NULL
        """
    )
    frappe.db.sql(
        """
        UPDATE `tabMembership Plan`
        SET student_price = 0
        WHERE student_price IS NULL
        """
    )

    members = frappe.get_all(
        "Gym Member",
        filters=[["membership_price", "in", ["", None, 0]]],
        fields=["name", "selected_plan", "customer_type"],
        limit_page_length=0,
    )
    for member in members:
        if not member.selected_plan:
            continue
        price_field = "student_price" if member.customer_type == "Student" else "regular_price"
        price = frappe.db.get_value("Membership Plan", member.selected_plan, price_field)
        if price is not None:
            frappe.db.set_value("Gym Member", member.name, "membership_price", price)

    frappe.db.sql(
        """
        UPDATE `tabGym Member`
        SET payment_status = 'Unpaid'
        WHERE IFNULL(payment_status, '') = ''
        """
    )
