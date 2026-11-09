document.addEventListener("DOMContentLoaded", function () {
    const calendarRoot = document.getElementById("calendar-week");
    const hoursRoot = document.getElementById("calendar-hours");
    const rangeLabel = document.getElementById("calendar-range");
    const selectedDateLabel = document.getElementById("calendar-selected-date");
    const feedback = document.getElementById("calendar-feedback");

    if (!calendarRoot || !hoursRoot || !rangeLabel || !selectedDateLabel || !feedback) {
        return;
    }

    const csrfToken = document.getElementById("trainer-calendar").dataset.csrfToken;
    const dateKey = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    };
    const parseDate = (key) => {
        const [year, month, day] = key.split("-").map(Number);
        return new Date(year, month - 1, day);
    };
    const addDays = (date, days) => {
        const result = new Date(date);
        result.setDate(result.getDate() + days);
        return result;
    };
    const mondayOf = (date) => {
        const result = new Date(date);
        result.setHours(0, 0, 0, 0);
        result.setDate(result.getDate() - ((result.getDay() + 6) % 7));
        return result;
    };
    const fullDate = new Intl.DateTimeFormat(undefined, {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
    });
    const today = new Date();
    let weekStart = mondayOf(today);
    let selectedDate = dateKey(today);
    let sessionsByHour = new Map();
    let isLoading = false;

    function call(method, args) {
        return fetch(`/api/method/${method}`, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Frappe-CSRF-Token": csrfToken,
            },
            body: new URLSearchParams(args),
        }).then(async (response) => {
            const result = await response.json();
            if (!response.ok) {
                let message = result.message;
                if (typeof message !== "string" && result._server_messages) {
                    try {
                        const serverMessages = JSON.parse(result._server_messages);
                        message = JSON.parse(serverMessages[0])?.message;
                    } catch (error) {
                        console.error("Could not read calendar API error:", error);
                    }
                }
                throw new Error(typeof message === "string" ? message : "Calendar request failed.");
            }
            if (result.message === undefined) {
                throw new Error("The server returned an empty response.");
            }
            return result.message;
        });
    }

    function showFeedback(message, isError = false) {
        feedback.textContent = message;
        feedback.classList.toggle("is-error", isError);
    }

    function renderWeek() {
        calendarRoot.replaceChildren();
        const weekEnd = addDays(weekStart, 6);
        rangeLabel.textContent = `${new Intl.DateTimeFormat(undefined, {
            month: "short",
            day: "numeric",
        }).format(weekStart)} – ${new Intl.DateTimeFormat(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
        }).format(weekEnd)}`;

        for (let offset = 0; offset < 7; offset += 1) {
            const date = addDays(weekStart, offset);
            const key = dateKey(date);
            const button = document.createElement("button");
            button.type = "button";
            button.className = "calendar-day";
            button.classList.toggle("is-selected", key === selectedDate);
            button.classList.toggle("is-today", key === dateKey(today));
            button.setAttribute("aria-pressed", String(key === selectedDate));

            const weekday = document.createElement("span");
            weekday.textContent = new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(date);
            const dayNumber = document.createElement("strong");
            dayNumber.textContent = String(date.getDate());
            const availableCount = [...sessionsByHour.values()].filter(
                (session) => session.slot_date === key && session.is_trainer_availability && !session.booking_count
            ).length;
            const availability = document.createElement("small");
            availability.textContent = `${availableCount} open`;
            button.append(weekday, dayNumber, availability);
            button.addEventListener("click", () => {
                selectedDate = key;
                showFeedback("");
                renderWeek();
                renderHours();
            });
            calendarRoot.append(button);
        }
    }

    function renderHours() {
        hoursRoot.replaceChildren();
        selectedDateLabel.textContent = fullDate.format(parseDate(selectedDate));
        const now = new Date();

        for (let hour = 0; hour < 24; hour += 1) {
            const slotKey = `${selectedDate}T${String(hour).padStart(2, "0")}`;
            const session = sessionsByHour.get(slotKey);
            const slot = document.createElement("article");
            slot.className = "calendar-hour";
            const timeLabel = document.createElement("time");
            timeLabel.className = "calendar-hour-time";
            timeLabel.textContent = `${String(hour).padStart(2, "0")}:00`;
            const details = document.createElement("div");
            details.className = "calendar-hour-details";
            const title = document.createElement("strong");
            const description = document.createElement("span");
            const actions = document.createElement("div");
            actions.className = "calendar-hour-actions";
            const slotDateTime = new Date(`${selectedDate}T${String(hour).padStart(2, "0")}:00`);
            const isPast = slotDateTime <= now;

            if (session?.is_trainer_availability && session.booking_count) {
                slot.classList.add("is-booked");
                title.textContent = "Booked";
                description.textContent = session.confirmed_members.join(", ");
                const status = document.createElement("span");
                status.className = "calendar-status";
                status.textContent = "Unavailable";
                actions.append(status);
            } else if (session?.is_trainer_availability) {
                slot.classList.add("is-available");
                title.textContent = "Available for booking";
                description.textContent = "One-hour appointment";
                const removeButton = document.createElement("button");
                removeButton.type = "button";
                removeButton.className = "calendar-action calendar-remove";
                removeButton.textContent = "Remove";
                removeButton.disabled = isPast || isLoading;
                removeButton.addEventListener("click", () => updateAvailability(
                    "gym_management.api.remove_trainer_availability",
                    { session_name: session.name },
                    "Availability removed."
                ));
                actions.append(removeButton);
            } else if (session) {
                slot.classList.add("has-session");
                title.textContent = session.session_name || "Scheduled session";
                description.textContent = "Already on your schedule";
                const status = document.createElement("span");
                status.className = "calendar-status";
                status.textContent = "Busy";
                actions.append(status);
            } else if (isPast) {
                slot.classList.add("is-past");
                title.textContent = "Past hour";
                description.textContent = "Availability can only be added for future hours";
            } else {
                title.textContent = "Not available";
                description.textContent = "Members cannot book this hour";
                const addButton = document.createElement("button");
                addButton.type = "button";
                addButton.className = "calendar-action";
                addButton.textContent = "Make available";
                addButton.disabled = isLoading;
                addButton.addEventListener("click", () => updateAvailability(
                    "gym_management.api.set_trainer_availability",
                    { slot_date: selectedDate, hour },
                    "This hour is now open for booking."
                ));
                actions.append(addButton);
            }

            details.append(title, description);
            slot.append(timeLabel, details, actions);
            hoursRoot.append(slot);
        }
    }

    async function loadWeek() {
        isLoading = true;
        showFeedback("Loading your calendar…");
        renderHours();
        try {
            const sessions = await call("gym_management.api.get_trainer_calendar", {
                start_date: dateKey(weekStart),
                days: 7,
            });
            sessionsByHour = new Map();
            sessions.forEach((session) => {
                const hour = String(session.slot_hour).padStart(2, "0");
                sessionsByHour.set(`${session.slot_date}T${hour}`, session);
            });
            showFeedback("");
        } catch (error) {
            showFeedback("Couldn't load the calendar. Please refresh and try again.", true);
            console.error(error);
        } finally {
            isLoading = false;
            renderWeek();
            renderHours();
        }
    }

    async function updateAvailability(method, args, successMessage) {
        isLoading = true;
        renderHours();
        showFeedback("Updating availability…");
        try {
            await call(method, args);
            showFeedback(successMessage);
            await loadWeek();
        } catch (error) {
            showFeedback(
                error?.message || "Couldn't update this hour. Please try again.",
                true
            );
            console.error(error);
        } finally {
            isLoading = false;
            renderWeek();
            renderHours();
        }
    }

    document.getElementById("calendar-previous").addEventListener("click", () => {
        weekStart = addDays(weekStart, -7);
        selectedDate = dateKey(weekStart);
        loadWeek();
    });
    document.getElementById("calendar-next").addEventListener("click", () => {
        weekStart = addDays(weekStart, 7);
        selectedDate = dateKey(weekStart);
        loadWeek();
    });
    document.getElementById("calendar-today").addEventListener("click", () => {
        weekStart = mondayOf(new Date());
        selectedDate = dateKey(new Date());
        loadWeek();
    });

    renderWeek();
    loadWeek();
});
