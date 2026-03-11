const state = {
  chart: null,
  seriesList: [],
};

const FRONTEND_DEV_PORTS = new Set(["3000", "4173", "5173", "5500", "5501", "5502"]);
const EVENT_COLORS_BY_CATEGORY = {
  fomc: "#7c3aed",
  inflation: "#be123c",
  labor: "#0f766e",
  growth: "#0369a1",
  housing: "#a16207",
};

const elements = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  seriesA: document.getElementById("seriesA"),
  seriesB: document.getElementById("seriesB"),
  eventCategory: document.getElementById("eventCategory"),
  startDate: document.getElementById("startDate"),
  endDate: document.getElementById("endDate"),
  compareBtn: document.getElementById("compareBtn"),
  status: document.getElementById("status"),
  canvas: document.getElementById("compareChart"),
};

const eventLinesPlugin = {
  id: "eventLines",
  beforeDatasetsDraw(chart, _args, pluginOptions) {
    const eventDates = pluginOptions?.dates || [];
    if (!eventDates.length) {
      return;
    }

    const xScale = chart.scales.x;
    if (!xScale) {
      return;
    }

    const { ctx, chartArea } = chart;
    ctx.save();
    ctx.strokeStyle = pluginOptions?.color || "rgba(17, 24, 39, 0.2)";
    ctx.lineWidth = pluginOptions?.lineWidth || 1;
    ctx.setLineDash(pluginOptions?.dash || [4, 4]);

    eventDates.forEach((dateLabel) => {
      const x = xScale.getPixelForValue(dateLabel);
      if (!Number.isFinite(x) || x < chartArea.left || x > chartArea.right) {
        return;
      }
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
    });

    ctx.restore();
  },
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

function inferApiBaseUrl() {
  const currentUrl = new URL(window.location.href);
  if (FRONTEND_DEV_PORTS.has(currentUrl.port)) {
    return `${currentUrl.protocol}//${currentUrl.hostname}:8000`;
  }
  return currentUrl.origin;
}

function normalizeBaseUrl(url) {
  const trimmed = url.trim().replace(/\/+$/, "");
  if (!trimmed) {
    return "";
  }
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  return `${window.location.protocol}//${trimmed}`;
}

function getApiBaseUrl() {
  const explicit = normalizeBaseUrl(elements.apiBaseUrl.value);
  if (explicit) {
    return explicit;
  }
  return inferApiBaseUrl();
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
    const contentType = response.headers.get("content-type") || "";
    const body = await response.text();
    if (contentType.includes("text/html")) {
      throw new Error(
        `${response.status} ${response.statusText}: expected JSON but got HTML. Verify API base URL: ${getApiBaseUrl()}`,
      );
    }
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
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
  const eventCategory = elements.eventCategory.value.trim();
  if (eventCategory) {
    params.append("event_category", eventCategory);
  }
  return `${apiBaseUrl}/compare?${params.toString()}`;
}

function renderChart(comparePayload) {
  const observationByDate = new Map(comparePayload.observations.map((row) => [row.date, row]));
  const eventDates = comparePayload.events.map((event) => event.event_date);
  const labels = Array.from(
    new Set([...comparePayload.observations.map((row) => row.date), ...eventDates]),
  ).sort();

  const valuesA = labels.map((date) => observationByDate.get(date)?.value_a ?? null);
  const valuesB = labels.map((date) => observationByDate.get(date)?.value_b ?? null);
  const eventsByDate = new Map();
  comparePayload.events.forEach((event) => {
    const eventsAtDate = eventsByDate.get(event.event_date) || [];
    eventsAtDate.push(event);
    eventsByDate.set(event.event_date, eventsAtDate);
  });

  const eventMarkerData = labels.map((date) => (eventsByDate.has(date) ? 1 : null));
  const eventMarkerColors = labels.map((date) => {
    const eventsAtDate = eventsByDate.get(date);
    if (!eventsAtDate?.length) {
      return "rgba(0, 0, 0, 0)";
    }
    const firstCategory = eventsAtDate[0].category || "";
    return EVENT_COLORS_BY_CATEGORY[firstCategory] || "#334155";
  });

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
        {
          label: "Events",
          data: eventMarkerData,
          type: "line",
          yAxisID: "eventAxis",
          pointRadius: 4,
          pointHoverRadius: 6,
          pointStyle: "rectRot",
          pointBackgroundColor: eventMarkerColors,
          pointBorderColor: eventMarkerColors,
          borderWidth: 0,
          showLine: false,
          spanGaps: true,
        },
      ],
    },
    plugins: [eventLinesPlugin],
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
        eventLines: {
          dates: eventDates,
        },
        tooltip: {
          callbacks: {
            label(context) {
              if (context.dataset.label === "Events") {
                return "Event marker";
              }
              const value =
                typeof context.parsed.y === "number"
                  ? context.parsed.y.toLocaleString()
                  : context.parsed.y;
              return `${context.dataset.label}: ${value}`;
            },
            afterBody(items) {
              const dateLabel = items[0]?.label;
              if (!dateLabel) {
                return [];
              }
              const eventsAtDate = eventsByDate.get(dateLabel) || [];
              if (!eventsAtDate.length) {
                return [];
              }
              const lines = ["Events:"];
              eventsAtDate.forEach((event) => {
                const category = event.category ? ` (${event.category})` : "";
                lines.push(`${event.title}${category}`);
                if (event.summary) {
                  lines.push(`- ${event.summary}`);
                }
              });
              return lines;
            },
          },
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
        eventAxis: {
          display: false,
          min: 0,
          max: 1,
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
  const categoryFilter = elements.eventCategory.value || "all";
  setStatus(
    `Rendered ${payload.observations.length} aligned dates (${pointsA} points for A, ${pointsB} points for B) with ${payload.events.length} events (${categoryFilter}).`,
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
  const normalizedApiBaseUrl = normalizeBaseUrl(elements.apiBaseUrl.value);
  const frontendOrigin = window.location.origin.replace(/\/+$/, "");
  if (!normalizedApiBaseUrl || normalizedApiBaseUrl === frontendOrigin) {
    elements.apiBaseUrl.value = inferApiBaseUrl();
  } else {
    elements.apiBaseUrl.value = normalizedApiBaseUrl;
  }

  elements.apiBaseUrl.addEventListener("blur", () => {
    elements.apiBaseUrl.value = normalizeBaseUrl(elements.apiBaseUrl.value);
  });

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
