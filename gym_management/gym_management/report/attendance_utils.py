import frappe
from frappe.utils import getdate, today


def get_attendance_records(filters):
    filters = frappe._dict(filters or {})
    from_date = getdate(filters.from_date or today())
    to_date = getdate(filters.to_date or today())
    if from_date > to_date:
        frappe.throw("From Date cannot be later than To Date.")

    query_filters = {"date": ["between", [from_date, to_date]]}
    if filters.member:
        query_filters["member"] = filters.member

    records = []
    start = 0
    page_length = 1000
    while True:
        page = frappe.get_all(
            "Member Attendance Log",
            filters=query_filters,
            fields=["name", "member", "date", "check_in_time", "workout_notes"],
            order_by="date asc, check_in_time asc",
            start=start,
            limit_page_length=page_length,
        )
        records.extend(page)
        if len(page) < page_length:
            break
        start += page_length

    member_names = sorted({record.member for record in records if record.member})
    member_names_by_id = {}
    if member_names:
        member_names_by_id = {
            member.name: member.full_name
            for member in frappe.get_all(
                "Gym Member",
                filters={"name": ["in", member_names]},
                fields=["name", "full_name"],
                limit_page_length=0,
            )
        }

    for record in records:
        record.member_name = member_names_by_id.get(record.member, "")

    return records
