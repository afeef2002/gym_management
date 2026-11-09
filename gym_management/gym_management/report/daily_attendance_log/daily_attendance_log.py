import frappe
from frappe import _

from ..attendance_utils import get_attendance_records


def execute(filters=None):
    columns = [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
        {"label": _("Member"), "fieldname": "member", "fieldtype": "Link", "options": "Gym Member", "width": 150},
        {"label": _("Member Name"), "fieldname": "member_name", "fieldtype": "Data", "width": 180},
        {"label": _("Check-in Time"), "fieldname": "check_in_time", "fieldtype": "Time", "width": 120},
        {"label": _("Workout Notes / Progress"), "fieldname": "workout_notes", "fieldtype": "Data", "width": 320},
    ]
    return columns, get_attendance_records(filters)
