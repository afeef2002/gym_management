import frappe


def execute():
    roles = {
        "Gym Receptionist": 1,
        "Gym Manager": 1,
        "Gym Member User": 0,
    }

    for role_name, desk_access in roles.items():
        if frappe.db.exists("Role", role_name):
            continue

        frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": desk_access,
                "is_custom": 1,
            }
        ).insert(ignore_permissions=True)
