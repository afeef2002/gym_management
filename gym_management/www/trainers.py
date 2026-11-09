import frappe

def get_context(context):
    context.no_cache = 1
    context.logged_in = frappe.session.user != "Guest"

    context.trainers = frappe.get_all(
        "Trainer",
        fields=[
            "name",
            "trainer_name",
            "email",
            "phone",
            "specialization",
            "bio"
        ],
        order_by="trainer_name asc"
    )