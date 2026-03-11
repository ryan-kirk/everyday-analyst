const state = {
  chart: null,
  seriesList: [],
  presets: [],
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
  presetSelect: document.getElementById("presetSelect"),
  presetDescription: document.getElementById("presetDescription"),
  eventCategory: document.getElementById("eventCategory"),
  startDate: document.getElementById("startDate"),
  endDate: document.getElementById("endDate"),
  compareBtn: document.getElementById("compareBtn"),
  status: document.getElementById("status"),
  canvas: document.getElementById("compareChart"),
  insightsLead: document.getElementById("insightsLead"),
  insightsSummary: document.getElementById("insightsSummary"),
  insightsMeta: document.getElementById("insightsMeta"),
  seriesContext: document.getElementById("seriesContext"),
  inflectionPoints: document.getElementById("inflectionPoints"),
  majorMovements: document.getElementById("majorMovements"),
  eventsTableBody: document.getElementById("eventsTableBody"),
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

function formatDate(isoDate) {
  if (!isoDate) {
    return "n/a";
  }
  const parsed = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return isoDate;
  }
  return parsed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

function formatNumber(value, digits = 3) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function formatPercent(value, digits = 1) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${(value * 100).toFixed(digits)}%`;
}

function escapeHtml(raw) {
  return String(raw)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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

function buildPresetsUrl() {
  return `${getApiBaseUrl()}/presets`;
}

function renderPresetOptions() {
  const optionsHtml = [
    `<option value="">Custom</option>`,
    ...state.presets.map((preset) => `<option value="${preset.id}">${preset.name}</option>`),
  ].join("");
  elements.presetSelect.innerHTML = optionsHtml;
}

async function loadPresets() {
  try {
    const presets = await fetchJson(buildPresetsUrl());
    state.presets = presets;
    renderPresetOptions();
  } catch (_error) {
    state.presets = [];
    renderPresetOptions();
    setStatus("Preset workflows are unavailable. Continuing in custom mode.", true);
  }
}

function resolveSeriesIdBySourceId(sourceSeriesId) {
  const series = state.seriesList.find((item) => item.source_series_id === sourceSeriesId);
  return series ? String(series.id) : null;
}

function applyRecommendedDateRange(rangeSpec) {
  if (!rangeSpec) {
    return;
  }

  const parsed = /^(\d+)\s*([dwmy])$/i.exec(rangeSpec.trim());
  if (!parsed) {
    return;
  }

  const amount = Number(parsed[1]);
  const unit = parsed[2].toLowerCase();
  const endDate = new Date();
  const startDate = new Date(endDate);

  if (unit === "d") {
    startDate.setDate(endDate.getDate() - amount);
  } else if (unit === "w") {
    startDate.setDate(endDate.getDate() - amount * 7);
  } else if (unit === "m") {
    startDate.setMonth(endDate.getMonth() - amount);
  } else if (unit === "y") {
    startDate.setFullYear(endDate.getFullYear() - amount);
  } else {
    return;
  }

  elements.startDate.value = startDate.toISOString().slice(0, 10);
  elements.endDate.value = endDate.toISOString().slice(0, 10);
}

function applyPreset(preset) {
  if (!preset) {
    elements.presetDescription.textContent =
      "Custom mode. Select any two series and date range for ad hoc analysis.";
    return;
  }

  const seriesAId = resolveSeriesIdBySourceId(preset.series_a);
  const seriesBId = resolveSeriesIdBySourceId(preset.series_b);

  if (seriesAId && seriesBId) {
    elements.seriesA.value = seriesAId;
    elements.seriesB.value = seriesBId;
  } else {
    setStatus(
      `Preset '${preset.name}' references unavailable series in this environment.`,
      true,
    );
  }

  applyRecommendedDateRange(preset.recommended_date_range);
  elements.presetDescription.textContent = `${preset.name}: ${preset.description} Recommended range: ${preset.recommended_date_range}.`;
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

function buildInsightsUrl() {
  const apiBaseUrl = getApiBaseUrl();
  const params = new URLSearchParams({
    series_a: elements.seriesA.value,
    series_b: elements.seriesB.value,
    start: elements.startDate.value,
    end: elements.endDate.value,
  });
  return `${apiBaseUrl}/insights?${params.toString()}`;
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
          yAxisID: "yLeft",
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
          yAxisID: "yRight",
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
        yLeft: {
          type: "linear",
          position: "left",
        },
        yRight: {
          type: "linear",
          position: "right",
          grid: {
            drawOnChartArea: false,
          },
        },
        eventAxis: {
          axis: "y",
          display: false,
          min: 0,
          max: 1,
        },
      },
    },
  });
}

function renderInsightsMeta(insightsPayload) {
  const correlation =
    insightsPayload.correlation === null || insightsPayload.correlation === undefined
      ? "n/a"
      : insightsPayload.correlation.toFixed(2);

  const metaRows = [
    ["Range", `${formatDate(insightsPayload.start)} - ${formatDate(insightsPayload.end)}`],
    ["Aligned Dates", formatNumber(insightsPayload.aligned_points, 0)],
    ["Series A Points", formatNumber(insightsPayload.series_a_points, 0)],
    ["Series B Points", formatNumber(insightsPayload.series_b_points, 0)],
    ["Overlap Points", formatNumber(insightsPayload.overlap_points, 0)],
    ["Correlation", correlation],
    ["Inflections", formatNumber(insightsPayload.inflection_points.length, 0)],
    ["Major Moves", formatNumber(insightsPayload.major_movements.length, 0)],
  ];

  elements.insightsMeta.innerHTML = metaRows
    .map(
      ([label, value]) =>
        `<div class="meta-item"><div class="meta-item-label">${escapeHtml(label)}</div><div class="meta-item-value">${escapeHtml(value)}</div></div>`,
    )
    .join("");
}

function renderSeriesContext(insightsPayload) {
  const seriesRows = [
    ["Series A", insightsPayload.series_a],
    ["Series B", insightsPayload.series_b],
  ];

  elements.seriesContext.innerHTML = seriesRows
    .map(([label, series]) => {
      const fields = [
        `ID: ${series.id}`,
        `Source: ${series.source}`,
        `Source ID: ${series.source_series_id}`,
        `Units: ${series.units || "n/a"}`,
        `Frequency: ${series.frequency || "n/a"}`,
        `Category: ${series.category || "n/a"}`,
      ];
      return `
        <div class="series-context-item">
          <div class="series-context-title">${escapeHtml(label)}: ${escapeHtml(series.name)}</div>
          <div class="series-context-meta">${escapeHtml(fields.join(" | "))}</div>
        </div>
      `;
    })
    .join("");
}

function formatNearbyEvents(events) {
  if (!events?.length) {
    return `<div class="nearby-events-item">No nearby events.</div>`;
  }
  return events
    .map((event) => {
      const score = event.importance_score === null ? "n/a" : formatNumber(event.importance_score, 2);
      const summary = event.summary ? ` - ${event.summary}` : "";
      const eventId = event.id === null || event.id === undefined ? "n/a" : String(event.id);
      return `
        <div class="nearby-events-item">
          ${escapeHtml(formatDate(event.event_date))}: ${escapeHtml(event.title)}
          (id ${escapeHtml(eventId)})
          (${escapeHtml(event.category || "uncategorized")}, score ${escapeHtml(score)}, ${escapeHtml(event.source || "unknown source")})
          ${escapeHtml(summary)}
        </div>
      `;
    })
    .join("");
}

function renderInflectionPoints(insightsPayload) {
  if (!insightsPayload.inflection_points.length) {
    elements.inflectionPoints.innerHTML = `<div class="empty-note">No inflection points detected.</div>`;
    return;
  }

  elements.inflectionPoints.innerHTML = `
    <ol class="insight-list">
      ${insightsPayload.inflection_points
        .map((point) => {
          const deltaText = formatNumber(point.delta, 3);
          return `
            <li>
              <strong>${escapeHtml(formatDate(point.date))}</strong> - Series ${escapeHtml(point.series.toUpperCase())}
              turned <strong>${escapeHtml(point.direction)}</strong> (delta ${escapeHtml(deltaText)}).
              <div class="nearby-events">${formatNearbyEvents(point.nearby_events)}</div>
            </li>
          `;
        })
        .join("")}
    </ol>
  `;
}

function renderMajorMovements(insightsPayload) {
  if (!insightsPayload.major_movements.length) {
    elements.majorMovements.innerHTML = `<div class="empty-note">No major movements detected.</div>`;
    return;
  }

  elements.majorMovements.innerHTML = `
    <ol class="insight-list">
      ${insightsPayload.major_movements
        .map((move) => {
          const changeText = formatNumber(move.change, 3);
          const percentText = formatPercent(move.percent_change, 1);
          return `
            <li>
              <strong>Series ${escapeHtml(move.series.toUpperCase())}</strong> moved
              <strong>${escapeHtml(move.direction)}</strong> from
              ${escapeHtml(formatDate(move.start_date))} to ${escapeHtml(formatDate(move.end_date))}
              (change ${escapeHtml(changeText)}, ${escapeHtml(percentText)}).
              <div class="nearby-events">${formatNearbyEvents(move.nearby_events)}</div>
            </li>
          `;
        })
        .join("")}
    </ol>
  `;
}

function renderInsights(insightsPayload) {
  elements.insightsLead.textContent =
    "This view identifies turning points and larger moves, then shows events that occurred near those dates. Event proximity is context, not proof of causation.";
  elements.insightsSummary.textContent = insightsPayload.narrative_summary;
  elements.insightsSummary.classList.remove("empty-note");

  renderInsightsMeta(insightsPayload);
  renderSeriesContext(insightsPayload);
  renderInflectionPoints(insightsPayload);
  renderMajorMovements(insightsPayload);
}

function renderInsightsError(message) {
  elements.insightsSummary.textContent = message;
  elements.insightsSummary.classList.add("empty-note");
  elements.insightsMeta.innerHTML = "";
  elements.seriesContext.innerHTML = `<div class="empty-note">Unable to load series context.</div>`;
  elements.inflectionPoints.innerHTML = `<div class="empty-note">Unable to load inflection points.</div>`;
  elements.majorMovements.innerHTML = `<div class="empty-note">Unable to load major movements.</div>`;
}

function renderEventsTable(events) {
  if (!events.length) {
    elements.eventsTableBody.innerHTML = `
      <tr>
        <td colspan="3" class="empty-note">No events in this date range for the selected filter.</td>
      </tr>
    `;
    return;
  }

  elements.eventsTableBody.innerHTML = events
    .map((event) => {
      const summary = event.summary || "No summary provided.";
      const title = event.category ? `${event.title} (${event.category})` : event.title;
      return `
        <tr>
          <td>${escapeHtml(formatDate(event.event_date))}</td>
          <td>${escapeHtml(title)}</td>
          <td>${escapeHtml(summary)}</td>
        </tr>
      `;
    })
    .join("");
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
  const comparePayload = await fetchJson(buildCompareUrl());
  let insightsPayload = null;
  try {
    insightsPayload = await fetchJson(buildInsightsUrl());
  } catch (error) {
    renderInsightsError(
      `Insights are currently unavailable for this selection: ${error.message}`,
    );
  }

  if (!comparePayload.observations.length) {
    if (state.chart) {
      state.chart.destroy();
      state.chart = null;
    }
    renderEventsTable(comparePayload.events);
    if (insightsPayload) {
      renderInsights(insightsPayload);
    }
    setStatus("No observations found in this date range.", true);
    return;
  }

  renderChart(comparePayload);
  renderEventsTable(comparePayload.events);
  if (insightsPayload) {
    renderInsights(insightsPayload);
  }

  const pointsA = comparePayload.observations.filter((row) => row.value_a !== null).length;
  const pointsB = comparePayload.observations.filter((row) => row.value_b !== null).length;
  const categoryFilter = elements.eventCategory.value || "all";
  setStatus(
    `Rendered ${comparePayload.observations.length} aligned dates (${pointsA} points for A, ${pointsB} points for B) with ${comparePayload.events.length} events (${categoryFilter}).`,
  );
}

async function handleRenderClick() {
  try {
    await loadComparison();
  } catch (error) {
    setStatus(`Failed to load comparison: ${error.message}`, true);
  }
}

async function handlePresetChange() {
  const presetId = elements.presetSelect.value;
  const selectedPreset = state.presets.find((item) => String(item.id) === presetId) || null;
  applyPreset(selectedPreset);
  try {
    await loadComparison();
  } catch (error) {
    setStatus(`Failed to apply preset: ${error.message}`, true);
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
  elements.presetSelect.addEventListener("change", handlePresetChange);

  try {
    await loadSeries();
    await loadPresets();
    if (state.presets.length) {
      elements.presetSelect.value = String(state.presets[0].id);
      applyPreset(state.presets[0]);
    } else {
      applyPreset(null);
    }
    await loadComparison();
  } catch (error) {
    setStatus(
      `Initialization failed: ${error.message}. Check API URL and CORS configuration.`,
      true,
    );
  }
}

init();
