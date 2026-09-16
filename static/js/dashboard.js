/* =========================================================
   Dashboard charts — fetches /api/dashboard and renders Chart.js
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    fetch("/api/dashboard")
        .then((res) => res.json())
        .then((data) => {
            renderMonthlyTrend(data.monthly_trend);
            renderCategoryDoughnut(data.category_distribution);
            renderDailySpending(data.daily_spending);
        })
        .catch((err) => console.error("Failed to load dashboard data:", err));
});

const PALETTE = ["#4F46E5", "#16A34A", "#F59E0B", "#EF4444", "#0EA5E9", "#DB2777", "#7C3AED", "#059669", "#CA8A04", "#0891B2"];

function renderMonthlyTrend(trend) {
    const ctx = document.getElementById("monthlyTrendChart");
    if (!ctx) return;

    new Chart(ctx, {
        type: "line",
        data: {
            labels: trend.labels,
            datasets: [
                {
                    label: "Total Spend",
                    data: trend.values,
                    borderColor: "#4F46E5",
                    backgroundColor: "rgba(79, 70, 229, 0.08)",
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 3,
                    pointBackgroundColor: "#4F46E5",
                },
            ],
        },
        options: chartOptions((ctxItem) => `${formatINR(ctxItem.raw)}`),
    });
}

function renderCategoryDoughnut(dist) {
    const ctx = document.getElementById("categoryDoughnutChart");
    if (!ctx) return;

    if (!dist.labels || dist.labels.length === 0) {
        drawEmptyCanvasMessage(ctx, "No expenses recorded this month yet");
        return;
    }

    const total = dist.values.reduce((a, b) => a + b, 0);

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: dist.labels,
            datasets: [
                {
                    data: dist.values,
                    backgroundColor: PALETTE,
                    borderWidth: 2,
                    borderColor: "#fff",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "68%",
            plugins: {
                legend: { position: "bottom", labels: { boxWidth: 10, padding: 14, font: { size: 11.5 } } },
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

function renderDailySpending(daily) {
    const ctx = document.getElementById("dailySpendingChart");
    if (!ctx) return;

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: daily.labels,
            datasets: [
                {
                    label: "Daily Spend",
                    data: daily.values,
                    backgroundColor: "#6366F1",
                    borderRadius: 5,
                    maxBarThickness: 22,
                },
            ],
        },
        options: chartOptions((ctxItem) => `${formatINR(ctxItem.raw)}`),
    });
}

function chartOptions(tooltipLabelFn) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: { label: (ctxItem) => ` ${tooltipLabelFn(ctxItem)}` },
            },
        },
        scales: {
            x: { grid: { display: false }, ticks: { font: { size: 11 } } },
            y: {
                grid: { color: "#EEF0F7" },
                ticks: {
                    font: { size: 11 },
                    callback: (value) => formatINR(value),
                },
            },
        },
    };
}

function drawEmptyCanvasMessage(canvas, message) {
    const ctx = canvas.getContext("2d");
    canvas.height = 220;
    ctx.font = "13px Inter, sans-serif";
    ctx.fillStyle = "#9AA1BD";
    ctx.textAlign = "center";
    ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}

