document.addEventListener("DOMContentLoaded", () => {
  // Get leaderboard data safely from HTML
  const dataEl = document.getElementById("leaderboard-data");
  const labels = JSON.parse(dataEl.dataset.labels);
  const scores = JSON.parse(dataEl.dataset.scores);
  const topScore = parseFloat(dataEl.dataset.topscore);

  // Animate progress bars
  document.querySelectorAll(".score-fill").forEach((bar) => {
    const width = bar.dataset.width;
    setTimeout(() => {
      bar.style.width = `${width}%`;
    }, 200);
  });

  // Render Chart.js bar chart
  const ctx = document.getElementById("scoreChart");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Scores",
          data: scores,
          backgroundColor: [
            "#4ade80", "#22d3ee", "#facc15",
            "#f97316", "#ef4444", "#a78bfa",
          ],
          borderRadius: 10,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true, ticks: { color: "#cbd5e1" } },
        x: { ticks: { color: "#cbd5e1" } },
      },
    },
  });
});
