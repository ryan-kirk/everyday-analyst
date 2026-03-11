const state = {
  chart: null,
  seriesList: [],
};

const elements = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  seriesA: document.getElementById("seriesA"),
  seriesB: document.getElementById("seriesB"),
  startDate: document.getElementById("startDate"),
  endDate: document.getElementById("endDate"),
  compareBtn: document.getElementById("compareBtn"),
  status: document.getElementById("status"),
  canvas: document.getElementById("compareChart"),
};

function setDefaultDates() {
  const today = new Date();
  const oneYearBack = new Date(today);
  oneYearBack.setFullYear(today.getFullYear() - 1);

  elements.startDate.value = oneYearBack.toISOString().slice(0, 10);
  elements.endDate.value = today.toISOString().slice(0, 10);
}

function setStatus(message, isError = false) {
  elements.status.textContent = message;
  elements.status.style.color = isError ? "#9f1239" : "#3e4f61";
}

function getApiBaseUrl() {
  const explicit = elements.apiBaseUrl.value.trim().replace(/\/+$/, "");
  if (explicit) {
    return explicit;
  }
  return window.location.origin;
}

function renderSeriesOptions() {
  const optionsHtml = state.seriesList
    .map((series) => {
      const label = `${series.name} (${series.source_series_id})`;
      return `<option value="${series.id}">${label}</option>`;
    })
    .join("");

  elements.seriesA.innerHTML = optionsHtml;
  elements.seriesB.innerHTML = optionsHtml;

  if (state.seriesList.length > 1) {
    elements.seriesA.value = String(state.seriesList[0].id);
    elements.seriesB.value = String(state.seriesList[1].id);
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${message}`);
  }
  return response.json();
}

async function loadSeries() {
  const apiBaseUrl = getApiBaseUrl();
  setStatus("Loading available series...");

  const series = await fetchJson(`${apiBaseUrl}/series`);
  state.seriesList = series;

  if (!state.seriesList.length) {
    setStatus("No series found. Load data first, then refresh.", true);
    return;
  }

  renderSeriesOptions();
  setStatus(`Loaded ${state.seriesList.length} series.`);
}

function buildCompareUrl() {
  const apiBaseUrl = getApiBaseUrl();
  const params = new URLSearchParams({
    series_a: elements.seriesA.value,
    series_b: elements.seriesB.value,
    start: elements.startDate.value,
    end: elements.endDate.value,
  });
  return `${apiBaseUrl}/compare?${params.toString()}`;
}

function renderChart(comparePayload) {
  const labels = comparePayload.observations.map((row) => row.date);
  const valuesA = comparePayload.observations.map((row) => row.value_a);
  const valuesB = comparePayload.observations.map((row) => row.value_b);
  const pointsA = valuesA.filter((value) => value !== null).length;
  const pointsB = valuesB.filter((value) => value !== null).length;
  const isSparseA = pointsA <= labels.length / 3;
  const isSparseB = pointsB <= labels.length / 3;

  if (state.chart) {
    state.chart.destroy();
  }

  state.chart = new Chart(elements.canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: comparePayload.series_a.name,
          data: valuesA,
          borderColor: "#155e75",
          backgroundColor: "rgba(21, 94, 117, 0.14)",
          borderWidth: 2,
          pointRadius: isSparseA ? 3 : 0,
          pointHoverRadius: isSparseA ? 5 : 3,
          spanGaps: isSparseA,
          tension: 0.2,
        },
        {
          label: comparePayload.series_b.name,
          data: valuesB,
          borderColor: "#9a3412",
          backgroundColor: "rgba(154, 52, 18, 0.14)",
          borderWidth: 2,
          pointRadius: isSparseB ? 3 : 0,
          pointHoverRadius: isSparseB ? 5 : 3,
          spanGaps: isSparseB,
          tension: 0.2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          position: "top",
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 9,
          },
        },
      },
    },
  });
}

async function loadComparison() {
  const seriesAId = elements.seriesA.value;
  const seriesBId = elements.seriesB.value;

  if (!seriesAId || !seriesBId) {
    setStatus("Choose two series to compare.", true);
    return;
  }

  if (seriesAId === seriesBId) {
    setStatus("Select different series for A and B.", true);
    return;
  }

  setStatus("Loading comparison...");
  const payload = await fetchJson(buildCompareUrl());

  if (!payload.observations.length) {
    if (state.chart) {
      state.chart.destroy();
      state.chart = null;
    }
    setStatus("No observations found in this date range.", true);
    return;
  }

  renderChart(payload);
  const pointsA = payload.observations.filter((row) => row.value_a !== null).length;
  const pointsB = payload.observations.filter((row) => row.value_b !== null).length;
  setStatus(
    `Rendered ${payload.observations.length} aligned dates (${pointsA} points for A, ${pointsB} points for B).`,
  );
}

async function handleRenderClick() {
  try {
    await loadComparison();
  } catch (error) {
    setStatus(`Failed to load comparison: ${error.message}`, true);
  }
}

async function init() {
  if (!elements.apiBaseUrl.value.trim()) {
    elements.apiBaseUrl.value = window.location.origin;
  }

  setDefaultDates();
  elements.compareBtn.addEventListener("click", handleRenderClick);

  try {
    await loadSeries();
    await loadComparison();
  } catch (error) {
    setStatus(
      `Initialization failed: ${error.message}. Check API URL and CORS configuration.`,
      true,
    );
  }
}

init();
