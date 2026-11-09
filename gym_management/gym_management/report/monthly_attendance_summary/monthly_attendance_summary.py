from collections import defaultdict

import frappe
from frappe import _

from ..attendance_utils import get_attendance_records


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.from_date:
        filters.from_date = frappe.utils.get_first_day(frappe.utils.today())
    if not filters.to_date:
        filters.to_date = frappe.utils.today()

    grouped = defaultdict(
        lambda: {
            "attendance_count": 0,
            "attendance_dates": set(),
            "workout_notes": [],
        }
    )

    records = get_attendance_records(filters)
    member_names = {record.member: record.member_name for record in records if record.member}

    for record in records:
        month = frappe.utils.getdate(record.date).strftime("%Y-%m")
        key = (month, record.member)
        grouped[key]["attendance_count"] += 1
        grouped[key]["attendance_dates"].add(record.date)
        if record.workout_notes:
            grouped[key]["workout_notes"].append(f"{record.date}: {record.workout_notes}")

    rows = []
    for (month, member), totals in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1] or ""),
    ):
        rows.append(
            {
                "month": month,
                "member": member,
                "member_name": member_names.get(member, ""),
                "attendance_count": totals["attendance_count"],
                "attendance_days": len(totals["attendance_dates"]),
                "workout_notes": "\n".join(totals["workout_notes"]),
            }
        )

    columns = [
        {"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 100},
        {"label": _("Member"), "fieldname": "member", "fieldtype": "Link", "options": "Gym Member", "width": 150},
        {"label": _("Member Name"), "fieldname": "member_name", "fieldtype": "Data", "width": 180},
        {"label": _("Attendance Entries"), "fieldname": "attendance_count", "fieldtype": "Int", "width": 130},
        {"label": _("Attendance Days"), "fieldname": "attendance_days", "fieldtype": "Int", "width": 130},
        {"label": _("Workout Notes / Progress"), "fieldname": "workout_notes", "fieldtype": "Data", "width": 350},
    ]
    return columns, rows
