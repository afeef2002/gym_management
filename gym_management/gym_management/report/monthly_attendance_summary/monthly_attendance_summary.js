frappe.query_reports["Monthly Attendance Summary"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: `${frappe.datetime.get_today().slice(0, 7)}-01`,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "member",
            label: __("Member"),
            fieldtype: "Link",
            options: "Gym Member",
        },
    ],
};
