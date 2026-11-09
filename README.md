### Gym Management

Gym Membership Management System

## Features

- Member registration with receptionist review followed by gym manager approval.
- Student and regular plan prices are snapshotted when a membership is created.
- Receptionists and managers can publish trainer-specific sessions with a date,
  time, and capacity. Members can filter upcoming slots by trainer and date.
- Active members can book upcoming trainer sessions; booking capacity is serialized
  and the assigned trainer is emailed after a successful booking.
- Daily attendance logs and a monthly attendance summary are available to gym staff.
- Public membership, trainer, and upcoming session pages.
- Role-restricted manager and trainer dashboards. Assign a trainer profile to a
  Frappe user and grant that account the **Gym Trainer** role to enable the
  trainer dashboard.
- Trainer availability calendar with one-hour booking slots. Trainers can add
  future open hours, booked hours are hidden from member search, and booked
  availability cannot be removed.
- The **Gym Billing Summary** print format shows subscription dates, plan price,
  amount paid, balance, and payment reference.

Payment amounts and references are currently recorded by gym staff; this app does
not process card or online payments.

After installing or updating the app, run `bench --site <site-name> migrate` to
sync DocTypes, roles, workflow, print format, and the attendance data migration.

The manager dashboard is available at `/gym_manager_dashboard` to Gym Managers
and System Managers. The trainer dashboard is available at `/trainer_dashboard`
to users with the Gym Trainer role and a linked Trainer profile. The public
session filter lists all Trainer records, including trainers without scheduled
sessions. Trainers can manage one-hour slots from the calendar on their
dashboard; members only see open slots.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app gym_management
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/gym_management
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
