/* =========================================================
   Analytics page charts — fetches /api/analytics and renders Chart.js
   ========================================================= */

const ANALYTICS_PALETTE = ["#4F46E5", "#16A34A", "#F59E0B", "#EF4444", "#0EA5E9", "#DB2777", "#7C3AED", "#059669", "#CA8A04", "#0891B2"];

document.addEventListener("DOMContentLoaded", () => {
    fetch("/api/analytics")
        .then((res) => res.json())
        .then((data) => {
            renderLineChart("monthlyTrendChart", data.monthly_trend, "#4F46E5");
            renderCategoryPie(data.category_distribution);
            renderPaymentDoughnut(data.payment_method_distribution);
            renderWeekdayBar(data.weekday_distribution);
            renderBarChart("weeklyChart", data.weekly_spending, "#6366F1");
            renderBarChart("dailyChart", data.daily_spending, "#16A34A");
        })
        .catch((err) => console.error("Failed to load analytics data:", err));
});

function baseTooltipOptions() {
    return {
        responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (item) => ` ${formatINR(item.raw)}` } },
        },
        scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10.5 } } },
            y: { grid: { color: "#EEF0F7" }, ticks: { font: { size: 10.5 }, callback: (v) => formatINR(v) } },
        },
    };
}

function renderLineChart(canvasId, dataset, color) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    new Chart(ctx, {
        type: "line",
        data: {
            labels: dataset.labels,
            datasets: [
                {
                    label: "Spend",
                    data: dataset.values,
                    borderColor: color,
                    backgroundColor: color + "18",
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 2.5,
                },
            ],
        },
        options: baseTooltipOptions(),
    });
}

function renderBarChart(canvasId, dataset, color) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: dataset.labels,
            datasets: [{ label: "Spend", data: dataset.values, backgroundColor: color, borderRadius: 5, maxBarThickness: 24 }],
        },
        options: baseTooltipOptions(),
    });
}

function renderCategoryPie(dist) {
    const ctx = document.getElementById("categoryChart");
    if (!ctx) return;
    if (!dist.labels || dist.labels.length === 0) return;

    const total = dist.values.reduce((a, b) => a + b, 0);

    new Chart(ctx, {
        type: "pie",
        data: {
            labels: dist.labels,
            datasets: [{ data: dist.values, backgroundColor: ANALYTICS_PALETTE, borderWidth: 2, borderColor: "#fff" }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "bottom", labels: { boxWidth: 10, padding: 12, font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: (item) => {
                            const pct = total ? ((item.raw / total) * 100).toFixed(1) : 0;
                            return ` ${item.label}: ${formatINR(item.raw)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}

function renderPaymentDoughnut(dist) {
    const ctx = document.getElementById("paymentChart");
    if (!ctx) return;
    if (!dist.labels || dist.labels.length === 0) return;

    const total = dist.values.reduce((a, b) => a + b, 0);

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: dist.labels,
            datasets: [{ data: dist.values, backgroundColor: ANALYTICS_PALETTE.slice().reverse(), borderWidth: 2, borderColor: "#fff" }],
        },
        options: {
            responsive: true,
            cutout: "62%",
            plugins: {
                legend: { position: "bottom", labels: { boxWidth: 10, padding: 12, font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: (item) => {
                            const pct = total ? ((item.raw / total) * 100).toFixed(1) : 0;
                            return ` ${item.label}: ${formatINR(item.raw)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}

function renderWeekdayBar(dist) {
    const ctx = document.getElementById("weekdayChart");
    if (!ctx) return;
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: dist.labels.map((d) => d.slice(0, 3)),
            datasets: [{ label: "Spend", data: dist.values, backgroundColor: "#F59E0B", borderRadius: 5, maxBarThickness: 28 }],
        },
        options: baseTooltipOptions(),
    });
}
