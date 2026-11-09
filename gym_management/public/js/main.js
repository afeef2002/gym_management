document.addEventListener("DOMContentLoaded", function () {

    const trainerFilter = document.getElementById("trainer-filter");
    const dateFilter = document.getElementById("date-filter");
    const clearFiltersButton = document.getElementById("clear-schedule-filters");
    const scheduleResults = document.getElementById("schedule-results");
    const scheduleSlots = Array.from(document.querySelectorAll(".schedule-slot"));
    const filterEmptyState = document.getElementById("no-filter-results");

    function filterSchedule() {
        if (!trainerFilter || !dateFilter || !scheduleResults) {
            return;
        }

        const selectedTrainer = trainerFilter.value;
        const selectedDate = dateFilter.value;
        let visibleCount = 0;

        scheduleSlots.forEach(function (slot) {
            const matchesTrainer = !selectedTrainer || slot.dataset.trainer === selectedTrainer;
            const matchesDate = !selectedDate || slot.dataset.date === selectedDate;
            slot.hidden = !(matchesTrainer && matchesDate);
            if (!slot.hidden) {
                visibleCount += 1;
            }
        });

        const hasSessions = scheduleSlots.length > 0;
        scheduleResults.textContent = hasSessions
            ? `${visibleCount} ${visibleCount === 1 ? "session" : "sessions"} found`
            : "";
        if (filterEmptyState) {
            filterEmptyState.hidden = !hasSessions || visibleCount > 0;
        }
    }

    if (trainerFilter && dateFilter && scheduleResults) {
        trainerFilter.addEventListener("change", filterSchedule);
        dateFilter.addEventListener("change", filterSchedule);

        if (clearFiltersButton) {
            clearFiltersButton.addEventListener("click", function () {
                trainerFilter.value = "";
                dateFilter.value = "";
                filterSchedule();
            });
        }

        filterSchedule();
    }

    // Find all Book Now buttons
    const bookingButtons = document.querySelectorAll(".book-button");

    bookingButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            // Get session ID
            const sessionName = button.dataset.session;

            if (!sessionName) {
                alert("Session information is missing.");
                return;
            }

            // Prevent multiple clicks
            button.disabled = true;
            button.textContent = "Booking...";

            const csrfToken = document.querySelector(".schedule-page").dataset.csrfToken;
            fetch("/api/method/gym_management.api.book_session", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Frappe-CSRF-Token": csrfToken,
                },
                body: new URLSearchParams({ session_name: sessionName }),
            })
                .then(async function (response) {
                    const result = await response.json();
                    if (!response.ok) {
                        let errorMessage = result.message;
                        if (typeof errorMessage !== "string" && result._server_messages) {
                            try {
                                const serverMessages = JSON.parse(result._server_messages);
                                errorMessage = JSON.parse(serverMessages[0])?.message;
                            } catch (error) {
                                console.error("Could not read booking API error:", error);
                            }
                        }
                        throw new Error(
                            typeof errorMessage === "string"
                                ? errorMessage
                                : "Booking failed. Please try again."
                        );
                    }
                    return result.message;
                })
                .then(function (result) {
                    if (!result?.message) {
                        throw new Error("The server returned an empty booking response.");
                    }
                    alert(result.message);
                    window.location.reload();
                })
                .catch(function (error) {
                    alert(error.message || "Booking failed. Please try again.");
                    button.disabled = false;
                    button.textContent = "Book Now";
                    console.error(error);
                });

        });

    });

});