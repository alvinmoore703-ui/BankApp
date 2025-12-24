console.log("Bank app loaded");

// Highlight flagged transactions
document.addEventListener("DOMContentLoaded", () => {
    const rows = document.querySelectorAll("table tbody tr");
    rows.forEach(row => {
        const flagged = row.querySelector("td:nth-child(4)").innerText; // Flagged column
        if (flagged === "1") {
            row.style.backgroundColor = "#FFE5E5"; // Light red highlight
        }
    });

    // Optional: alert if a transfer was just made
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("transfer") && urlParams.get("transfer") === "success") {
        alert("Transfer successful!");
    }
});
