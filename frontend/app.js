const state = {
  chart: null,
  seriesList: [],
  presets: [],
  apiBaseUrl: null,
  user: null,
  activeSavedAnalysis: null,
  activeNotes: [],
  savedViews: [],
};

const FRONTEND_DEV_PORTS = new Set(["3000", "4173", "5173", "5500", "5501", "5502"]);
const ACTIVE_SAVED_VIEW_STORAGE_KEY_PREFIX = "ea_active_saved_view_user_";
const DEFAULT_EVENT_CATEGORIES = ["fomc", "inflation", "labor", "growth", "housing"];
const EVENT_COLORS_BY_CATEGORY = {
  fomc: "#7c3aed",
  inflation: "#be123c",
  labor: "#0f766e",
  growth: "#0369a1",
  housing: "#a16207",
};
const EVENT_CATEGORY_LABELS = {
  fomc: "FOMC",
  inflation: "Inflation",
  labor: "Labor",
  growth: "Growth",
  housing: "Housing",
  market: "Market",
  consumer: "Consumer",
  population: "Population",
};

const elements = {
  seriesA: document.getElementById("seriesA"),
  seriesB: document.getElementById("seriesB"),
  presetSelect: document.getElementById("presetSelect"),
  presetDescription: document.getElementById("presetDescription"),
  seriesASearch: document.getElementById("seriesASearch"),
  seriesBSearch: document.getElementById("seriesBSearch"),
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

  usernameInput: document.getElementById("usernameInput"),
  passwordInput: document.getElementById("passwordInput"),
  loginBtn: document.getElementById("loginBtn"),
  registerBtn: document.getElementById("registerBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  authFormControls: document.getElementById("authFormControls"),
  loggedInControls: document.getElementById("loggedInControls"),
  workspaceUserLabel: document.getElementById("workspaceUserLabel"),
  analysisTitleInput: document.getElementById("analysisTitleInput"),
  saveViewBtn: document.getElementById("saveViewBtn"),
  bookmarkViewBtn: document.getElementById("bookmarkViewBtn"),
  shareViewBtn: document.getElementById("shareViewBtn"),
  deleteViewBtn: document.getElementById("deleteViewBtn"),
  savedViewsSelect: document.getElementById("savedViewsSelect"),
  loadSavedViewBtn: document.getElementById("loadSavedViewBtn"),
  shareNotesToggle: document.getElementById("shareNotesToggle"),
  workspaceStatus: document.getElementById("workspaceStatus"),
  shareLinkText: document.getElementById("shareLinkText"),

  noteInput: document.getElementById("noteInput"),
  saveNoteBtn: document.getElementById("saveNoteBtn"),
  notesTableBody: document.getElementById("notesTableBody"),
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

function inferApiBaseUrl() {
  const currentUrl = new URL(window.location.href);
  if (FRONTEND_DEV_PORTS.has(currentUrl.port)) {
    return `${currentUrl.protocol}//${currentUrl.hostname}:8000`;
  }
  return currentUrl.origin;
}

function getApiBaseUrl() {
  if (!state.apiBaseUrl) {
    state.apiBaseUrl = inferApiBaseUrl();
  }
  return state.apiBaseUrl;
}

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

function setWorkspaceStatus(message, isError = false) {
  elements.workspaceStatus.textContent = message;
  elements.workspaceStatus.style.color = isError ? "#9f1239" : "#3e4f61";
}

function setShareLinkText(text = "") {
  elements.shareLinkText.textContent = text;
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

async function fetchJson(url, options = {}) {
  const requestOptions = { ...options };

  if (requestOptions.body && typeof requestOptions.body !== "string") {
    requestOptions.headers = {
      "Content-Type": "application/json",
      ...(requestOptions.headers || {}),
    };
    requestOptions.body = JSON.stringify(requestOptions.body);
  }

  const response = await fetch(url, requestOptions);
  const contentType = response.headers.get("content-type") || "";

  if (!response.ok) {
    let messageBody = await response.text();
    if (contentType.includes("application/json")) {
      try {
        const parsed = JSON.parse(messageBody);
        if (parsed && typeof parsed === "object" && parsed.detail) {
          messageBody = String(parsed.detail);
        }
      } catch (_error) {
        // keep raw body
      }
    } else if (contentType.includes("text/html")) {
      messageBody = "expected JSON but got HTML (verify backend server and CORS).";
    }

    throw new Error(`${response.status} ${response.statusText}: ${messageBody}`);
  }

  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

function renderSeriesOptions() {
  const currentSeriesAId = elements.seriesA.value;
  const currentSeriesBId = elements.seriesB.value;
  const filteredForA = filterSeriesBySearch(elements.seriesASearch.value);
  const filteredForB = filterSeriesBySearch(elements.seriesBSearch.value);

  const defaultSeriesAId = state.seriesList[0] ? String(state.seriesList[0].id) : "";
  const defaultSeriesBId = state.seriesList[1] ? String(state.seriesList[1].id) : defaultSeriesAId;

  const selectedA = renderSeriesSelect(
    elements.seriesA,
    filteredForA,
    currentSeriesAId,
    defaultSeriesAId,
  );
  const fallbackB = defaultSeriesBId && defaultSeriesBId !== selectedA ? defaultSeriesBId : defaultSeriesAId;
  let selectedB = renderSeriesSelect(elements.seriesB, filteredForB, currentSeriesBId, fallbackB);

  if (selectedA && selectedB && selectedA === selectedB) {
    const alternate =
      filteredForB.find((series) => String(series.id) !== selectedA) ||
      state.seriesList.find((series) => String(series.id) !== selectedA) ||
      null;
    if (alternate) {
      selectedB = String(alternate.id);
      elements.seriesB.value = selectedB;
    }
  }
}

function filterSeriesBySearch(rawQuery) {
  const query = String(rawQuery || "").trim().toLowerCase();
  if (!query) {
    return state.seriesList;
  }

  return state.seriesList.filter((series) => {
    const haystack = [
      series.name || "",
      series.source_series_id || "",
      series.source || "",
      series.category || "",
      series.units || "",
      series.frequency || "",
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function renderSeriesSelect(selectElement, filteredSeries, currentValue, fallbackValue) {
  const current = String(currentValue || "");
  const currentSeries =
    state.seriesList.find((series) => String(series.id) === current) || null;

  let options = [...filteredSeries];
  if (currentSeries && !options.some((series) => String(series.id) === current)) {
    options = [currentSeries, ...options];
  }

  if (!options.length) {
    selectElement.innerHTML = `<option value="">No matching series</option>`;
    selectElement.value = "";
    return "";
  }

  selectElement.innerHTML = options
    .map((series) => {
      const label = `${series.name} (${series.source_series_id})`;
      return `<option value="${series.id}">${escapeHtml(label)}</option>`;
    })
    .join("");

  const fallback = String(fallbackValue || "");
  if (currentSeries && options.some((series) => String(series.id) === current)) {
    selectElement.value = current;
    return current;
  }
  if (fallback && options.some((series) => String(series.id) === fallback)) {
    selectElement.value = fallback;
    return fallback;
  }
  const firstId = String(options[0].id);
  selectElement.value = firstId;
  return firstId;
}

function renderPresetOptions() {
  const optionsHtml = [
    `<option value="">Custom</option>`,
    ...state.presets.map((preset) => `<option value="${preset.id}">${preset.name}</option>`),
  ].join("");
  elements.presetSelect.innerHTML = optionsHtml;
}

function formatEventCategoryLabel(category) {
  return EVENT_CATEGORY_LABELS[category] || category.charAt(0).toUpperCase() + category.slice(1);
}

function renderEventCategoryOptions(categories) {
  const current = String(elements.eventCategory.value || "").trim().toLowerCase();
  const normalized = Array.from(
    new Set(
      (categories || [])
        .map((value) => String(value || "").trim().toLowerCase())
        .filter(Boolean),
    ),
  );
  const options = normalized.length ? normalized : DEFAULT_EVENT_CATEGORIES;

  elements.eventCategory.innerHTML = [
    `<option value="">All</option>`,
    ...options.map((category) => {
      return `<option value="${escapeHtml(category)}">${escapeHtml(formatEventCategoryLabel(category))}</option>`;
    }),
  ].join("");

  if (current && options.includes(current)) {
    elements.eventCategory.value = current;
  }
}

function renderSavedViewsOptions() {
  if (!state.user) {
    elements.savedViewsSelect.innerHTML = `<option value="">Log in to view saved analyses</option>`;
    return;
  }

  if (!state.savedViews.length) {
    elements.savedViewsSelect.innerHTML = `<option value="">No saved views yet</option>`;
    return;
  }

  elements.savedViewsSelect.innerHTML = [
    `<option value="">Select saved view...</option>`,
    ...state.savedViews.map(
      (view) => `<option value="${view.id}">${escapeHtml(formatSavedViewOptionLabel(view))}</option>`,
    ),
  ].join("");
}

function formatSavedViewOptionLabel(view) {
  const bookmarkFlag = view.is_bookmarked ? " ★" : "";
  const createdDate = view.created_at?.slice?.(0, 10) ? formatDate(view.created_at.slice(0, 10)) : "n/a";
  return `${view.title}${bookmarkFlag} (#${view.id}, ${createdDate})`;
}

function getSavedViewStorageKey(userId) {
  return `${ACTIVE_SAVED_VIEW_STORAGE_KEY_PREFIX}${userId}`;
}

function persistActiveSavedViewId(viewId) {
  if (!state.user) {
    return;
  }
  try {
    const key = getSavedViewStorageKey(state.user.id);
    if (!viewId) {
      localStorage.removeItem(key);
      return;
    }
    localStorage.setItem(key, String(viewId));
  } catch (_error) {
    // localStorage may be unavailable; continue without persistence.
  }
}

function readPersistedActiveSavedViewId() {
  if (!state.user) {
    return null;
  }
  try {
    const raw = localStorage.getItem(getSavedViewStorageKey(state.user.id));
    if (!raw) {
      return null;
    }
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  } catch (_error) {
    return null;
  }
}

async function loadSeries() {
  setStatus("Loading available series...");

  const series = await fetchJson(`${getApiBaseUrl()}/series`);
  state.seriesList = series;

  if (!state.seriesList.length) {
    setStatus("No series found. Load data first, then refresh.", true);
    return;
  }

  renderSeriesOptions();
  setStatus(`Loaded ${state.seriesList.length} series.`);
}

async function loadPresets() {
  try {
    const presets = await fetchJson(`${getApiBaseUrl()}/presets`);
    state.presets = presets;
    renderPresetOptions();
  } catch (_error) {
    state.presets = [];
    renderPresetOptions();
    setStatus("Preset workflows are unavailable. Continuing in custom mode.", true);
  }
}

async function loadEventCategories() {
  try {
    const categories = await fetchJson(`${getApiBaseUrl()}/events/categories`);
    if (Array.isArray(categories)) {
      renderEventCategoryOptions(categories);
      return;
    }
  } catch (_error) {
    // fall through to defaults
  }
  renderEventCategoryOptions(DEFAULT_EVENT_CATEGORIES);
}

async function loadSavedViews() {
  if (!state.user) {
    state.savedViews = [];
    renderSavedViewsOptions();
    return;
  }

  try {
    const views = await fetchJson(`${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses`);
    state.savedViews = views;
    renderSavedViewsOptions();

    if (state.activeSavedAnalysis) {
      const matched = views.find((view) => view.id === state.activeSavedAnalysis.id);
      if (!matched) {
        state.activeSavedAnalysis = null;
        state.activeNotes = [];
        renderNotesTable([]);
        selectSavedViewOption(null);
        elements.shareNotesToggle.checked = false;
        setShareLinkText("");
      } else {
        state.activeSavedAnalysis = matched;
        selectSavedViewOption(matched.id);
        elements.shareNotesToggle.checked = Boolean(matched.share_include_notes);
      }
    }
  } catch (error) {
    setWorkspaceStatus(`Failed to load saved views: ${error.message}`, true);
  }
}

function resolveSeriesIdBySourceId(sourceSeriesId) {
  const series = state.seriesList.find((item) => item.source_series_id === sourceSeriesId);
  return series ? String(series.id) : null;
}

function buildSeriesInfoLink(series) {
  const source = String(series.source || "").toLowerCase();
  const sourceSeriesId = String(series.source_series_id || "").trim();
  if (!sourceSeriesId) {
    return null;
  }

  if (source === "fred") {
    return `https://fred.stlouisfed.org/series/${encodeURIComponent(sourceSeriesId)}`;
  }
  if (source === "bls") {
    return `https://data.bls.gov/timeseries/${encodeURIComponent(sourceSeriesId)}`;
  }
  return null;
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

function buildCompareUrl() {
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
  return `${getApiBaseUrl()}/compare?${params.toString()}`;
}

function buildInsightsUrl() {
  const params = new URLSearchParams({
    series_a: elements.seriesA.value,
    series_b: elements.seriesB.value,
    start: elements.startDate.value,
    end: elements.endDate.value,
  });
  return `${getApiBaseUrl()}/insights?${params.toString()}`;
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
          spanGaps: true,
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
          spanGaps: true,
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
    ["Overlap Method", insightsPayload.overlap_method || "n/a"],
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
      const link = buildSeriesInfoLink(series);
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
          ${
            link
              ? `<div class="series-context-link"><a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">Open source series details</a></div>`
              : ""
          }
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
              <strong>${escapeHtml(formatDate(point.date))}</strong> - ${escapeHtml(point.series)}
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
              <strong>${escapeHtml(move.series)}</strong> moved
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

function getSelectedSeriesById(seriesId) {
  return state.seriesList.find((series) => String(series.id) === String(seriesId)) || null;
}

function getDefaultAnalysisTitle() {
  const seriesA = getSelectedSeriesById(elements.seriesA.value);
  const seriesB = getSelectedSeriesById(elements.seriesB.value);
  const nameA = seriesA ? seriesA.name : "Series A";
  const nameB = seriesB ? seriesB.name : "Series B";
  return `${nameA} vs ${nameB} (${elements.startDate.value} to ${elements.endDate.value})`;
}

function applySavedAnalysisToControls(saved) {
  if (!saved) {
    return;
  }
  if (saved.series_a_id) {
    elements.seriesA.value = String(saved.series_a_id);
  }
  if (saved.series_b_id) {
    elements.seriesB.value = String(saved.series_b_id);
  }
  if (saved.start_date) {
    elements.startDate.value = saved.start_date;
  }
  if (saved.end_date) {
    elements.endDate.value = saved.end_date;
  }

  elements.eventCategory.value = saved.event_category_filter || "";
  elements.analysisTitleInput.value = saved.title || "";
  elements.shareNotesToggle.checked = Boolean(saved.share_include_notes);
}

function selectSavedViewOption(viewId) {
  if (!viewId) {
    elements.savedViewsSelect.value = "";
    return;
  }
  elements.savedViewsSelect.value = String(viewId);
}

function getActiveOwnedAnalysis() {
  if (!state.user || !state.activeSavedAnalysis) {
    return null;
  }
  if (state.activeSavedAnalysis.user_id !== state.user.id) {
    return null;
  }
  return state.activeSavedAnalysis;
}

function buildShareUrlFromToken(token) {
  if (!token) {
    return "";
  }
  const shareUrl = new URL(window.location.href);
  shareUrl.searchParams.set("share", token);
  return shareUrl.toString();
}

function renderShareLinkFromToken(token) {
  const shareUrl = buildShareUrlFromToken(token);
  if (!shareUrl) {
    setShareLinkText("");
    return "";
  }
  setShareLinkText(`Share link: ${shareUrl}`);
  return shareUrl;
}

function renderNotesTable(notes) {
  const canDelete = Boolean(getActiveOwnedAnalysis());
  if (!notes.length) {
    elements.notesTableBody.innerHTML = `
      <tr>
        <td colspan="3" class="empty-note">No notes saved for this view yet.</td>
      </tr>
    `;
    return;
  }

  elements.notesTableBody.innerHTML = notes
    .map(
      (note) => `
        <tr>
          <td>${escapeHtml(formatDate(note.created_at?.slice?.(0, 10) || ""))}</td>
          <td>${escapeHtml(note.note_text)}</td>
          <td>
            ${
              canDelete
                ? `<button class="muted-btn notes-delete-btn" data-note-id="${note.id}" type="button">Delete</button>`
                : `<span class="empty-note">Read only</span>`
            }
          </td>
        </tr>
      `,
    )
    .join("");

  if (canDelete) {
    const buttons = elements.notesTableBody.querySelectorAll("[data-note-id]");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        deleteNote(button.getAttribute("data-note-id"));
      });
    });
  }
}

function clearWorkspaceSelectionContext() {
  if (!state.activeSavedAnalysis) {
    return;
  }
  state.activeSavedAnalysis = null;
  state.activeNotes = [];
  renderNotesTable(state.activeNotes);
  elements.shareNotesToggle.checked = false;
  selectSavedViewOption(null);
  setShareLinkText("");
  updateWorkspaceUserLabel();
}

async function restoreActiveSavedViewAfterLogin() {
  if (!state.user || !state.savedViews.length) {
    state.activeSavedAnalysis = null;
    state.activeNotes = [];
    renderNotesTable(state.activeNotes);
    selectSavedViewOption(null);
    return;
  }

  const ownedActive = getActiveOwnedAnalysis();
  if (ownedActive) {
    selectSavedViewOption(ownedActive.id);
    elements.shareNotesToggle.checked = Boolean(ownedActive.share_include_notes);
    await refreshNotes();
    return;
  }

  const persistedId = readPersistedActiveSavedViewId();
  const preferredView =
    state.savedViews.find((view) => view.id === persistedId) || state.savedViews[0] || null;
  if (!preferredView) {
    return;
  }

  state.activeSavedAnalysis = preferredView;
  applySavedAnalysisToControls(preferredView);
  selectSavedViewOption(preferredView.id);
  elements.shareNotesToggle.checked = Boolean(preferredView.share_include_notes);
  renderShareLinkFromToken(preferredView.share_token);
  persistActiveSavedViewId(preferredView.id);
  await refreshNotes();

  try {
    await loadComparison();
  } catch (error) {
    setStatus(`Loaded saved view but compare failed: ${error.message}`, true);
  }
}

function requireLoggedIn(action) {
  if (state.user) {
    return true;
  }
  setWorkspaceStatus(`Log in before ${action}.`, true);
  return false;
}

function updateWorkspaceUserLabel() {
  if (!state.user) {
    elements.authFormControls.classList.remove("hidden");
    elements.loggedInControls.classList.add("hidden");
    elements.workspaceUserLabel.textContent = "";
    setWorkspaceStatus("Not logged in.");
    return;
  }
  elements.authFormControls.classList.add("hidden");
  elements.loggedInControls.classList.remove("hidden");
  elements.workspaceUserLabel.textContent = `Logged in as ${state.user.username}`;
  setWorkspaceStatus(`Logged in as ${state.user.username}.`);
}

async function registerUser() {
  const username = elements.usernameInput.value.trim().toLowerCase();
  const password = elements.passwordInput.value;

  if (!username || !password) {
    setWorkspaceStatus("Enter both username and password to register.", true);
    return;
  }

  const payload = {
    username,
    password,
    name: username,
  };

  try {
    const user = await fetchJson(`${getApiBaseUrl()}/workspace/users`, {
      method: "POST",
      body: payload,
    });
    state.user = user;
    elements.passwordInput.value = "";
    updateWorkspaceUserLabel();
    await loadSavedViews();
    setWorkspaceStatus(`Account created and logged in as ${user.username}.`);
  } catch (error) {
    setWorkspaceStatus(`Registration failed: ${error.message}`, true);
  }
}

async function loginUser() {
  const username = elements.usernameInput.value.trim().toLowerCase();
  const password = elements.passwordInput.value;

  if (!username || !password) {
    setWorkspaceStatus("Enter both username and password to log in.", true);
    return;
  }

  try {
    const user = await fetchJson(`${getApiBaseUrl()}/workspace/auth/login`, {
      method: "POST",
      body: { username, password },
    });
    state.user = user;
    elements.passwordInput.value = "";
    updateWorkspaceUserLabel();
    await loadSavedViews();
    await restoreActiveSavedViewAfterLogin();
    setWorkspaceStatus(`Logged in as ${user.username}.`);
  } catch (error) {
    setWorkspaceStatus(`Login failed: ${error.message}`, true);
  }
}

function logoutUser() {
  state.user = null;
  state.savedViews = [];
  state.activeSavedAnalysis = null;
  state.activeNotes = [];
  renderNotesTable([]);
  selectSavedViewOption(null);
  elements.shareNotesToggle.checked = false;
  setShareLinkText("");
  renderSavedViewsOptions();
  updateWorkspaceUserLabel();
  setWorkspaceStatus("Logged out.");
}

async function saveView() {
  if (!requireLoggedIn("saving a view")) {
    return;
  }

  if (!elements.seriesA.value || !elements.seriesB.value) {
    setWorkspaceStatus("Pick two series before saving a view.", true);
    return;
  }

  const title = elements.analysisTitleInput.value.trim() || getDefaultAnalysisTitle();
  const payload = {
    title,
    description: "Saved from Everyday Analyst web view",
    series_a_id: Number(elements.seriesA.value),
    series_b_id: Number(elements.seriesB.value),
    start_date: elements.startDate.value || null,
    end_date: elements.endDate.value || null,
    event_category_filter: elements.eventCategory.value || null,
    is_bookmarked: Boolean(getActiveOwnedAnalysis()?.is_bookmarked),
    share_include_notes: Boolean(elements.shareNotesToggle.checked),
  };

  try {
    const saved = await fetchJson(`${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses`, {
      method: "POST",
      body: payload,
    });

    state.activeSavedAnalysis = saved;
    elements.analysisTitleInput.value = saved.title;
    elements.shareNotesToggle.checked = Boolean(saved.share_include_notes);
    selectSavedViewOption(saved.id);
    renderShareLinkFromToken(saved.share_token);
    persistActiveSavedViewId(saved.id);
    setWorkspaceStatus(`Saved view: ${saved.title}`);
    await loadSavedViews();
    await refreshNotes();
  } catch (error) {
    setWorkspaceStatus(`Save failed: ${error.message}`, true);
  }
}

async function toggleBookmark() {
  if (!requireLoggedIn("bookmarking")) {
    return;
  }

  let analysis = getActiveOwnedAnalysis();
  if (!analysis) {
    await saveView();
    analysis = getActiveOwnedAnalysis();
    if (!analysis) {
      return;
    }
  }

  try {
    const updated = await fetchJson(
      `${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses/${analysis.id}/bookmark`,
      {
        method: "PATCH",
        body: { is_bookmarked: !analysis.is_bookmarked },
      },
    );
    state.activeSavedAnalysis = updated;
    selectSavedViewOption(updated.id);
    persistActiveSavedViewId(updated.id);
    const bookmarkText = updated.is_bookmarked ? "bookmarked" : "unbookmarked";
    setWorkspaceStatus(`View ${bookmarkText}.`);
    await loadSavedViews();
  } catch (error) {
    setWorkspaceStatus(`Bookmark update failed: ${error.message}`, true);
  }
}

async function deleteView() {
  if (!requireLoggedIn("deleting a saved view")) {
    return;
  }

  const analysis = getActiveOwnedAnalysis();
  if (!analysis) {
    setWorkspaceStatus("Load one of your saved views before deleting.", true);
    return;
  }

  const confirmed = window.confirm(
    `Delete saved view "${analysis.title}"? This will also delete notes for this view.`,
  );
  if (!confirmed) {
    return;
  }

  try {
    await fetchJson(
      `${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses/${analysis.id}`,
      { method: "DELETE" },
    );

    persistActiveSavedViewId(null);
    state.activeSavedAnalysis = null;
    state.activeNotes = [];
    renderNotesTable(state.activeNotes);
    selectSavedViewOption(null);
    setShareLinkText("");
    elements.shareNotesToggle.checked = false;

    await loadSavedViews();
    await restoreActiveSavedViewAfterLogin();
    setWorkspaceStatus(`Deleted saved view: ${analysis.title}`);
  } catch (error) {
    setWorkspaceStatus(`Delete failed: ${error.message}`, true);
  }
}

async function shareView() {
  let analysis = state.activeSavedAnalysis;
  if (!analysis || !analysis.share_token) {
    await saveView();
    analysis = state.activeSavedAnalysis;
  }

  if (!analysis?.share_token) {
    setWorkspaceStatus("Save a view before sharing.", true);
    return;
  }

  const owned = getActiveOwnedAnalysis();
  if (owned && owned.share_include_notes !== Boolean(elements.shareNotesToggle.checked)) {
    await updateShareSettings();
    analysis = state.activeSavedAnalysis;
  }

  const shareUrl = renderShareLinkFromToken(analysis.share_token);
  if (!shareUrl) {
    return;
  }

  try {
    await navigator.clipboard.writeText(shareUrl);
    setWorkspaceStatus("Share link copied to clipboard.");
  } catch (_error) {
    setWorkspaceStatus("Share link generated (copy manually from the line below).");
  }
}

async function refreshNotes() {
  if (!state.activeSavedAnalysis) {
    state.activeNotes = [];
    renderNotesTable(state.activeNotes);
    return;
  }

  const owned = getActiveOwnedAnalysis();
  if (!owned) {
    renderNotesTable(state.activeNotes);
    return;
  }

  try {
    const notes = await fetchJson(
      `${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses/${owned.id}/notes`,
    );
    state.activeNotes = notes;
    renderNotesTable(state.activeNotes);
  } catch (error) {
    setWorkspaceStatus(`Failed to load notes: ${error.message}`, true);
  }
}

async function saveNote() {
  if (!requireLoggedIn("saving notes")) {
    return;
  }

  let analysis = getActiveOwnedAnalysis();
  if (!analysis) {
    await saveView();
    analysis = getActiveOwnedAnalysis();
    if (!analysis) {
      return;
    }
  }

  const noteText = elements.noteInput.value.trim();
  if (!noteText) {
    setWorkspaceStatus("Enter a note before saving.", true);
    return;
  }

  try {
    await fetchJson(
      `${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses/${analysis.id}/notes`,
      {
        method: "POST",
        body: { note_text: noteText },
      },
    );

    elements.noteInput.value = "";
    await refreshNotes();
    setWorkspaceStatus("Note saved.");
  } catch (error) {
    setWorkspaceStatus(`Failed to save note: ${error.message}`, true);
  }
}

async function deleteNote(noteIdRaw) {
  if (!requireLoggedIn("deleting notes")) {
    return;
  }
  const analysis = getActiveOwnedAnalysis();
  if (!analysis) {
    setWorkspaceStatus("Load one of your saved views to delete notes.", true);
    return;
  }

  const noteId = Number(noteIdRaw);
  if (!Number.isFinite(noteId)) {
    setWorkspaceStatus("Invalid note id.", true);
    return;
  }

  try {
    await fetchJson(
      `${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses/${analysis.id}/notes/${noteId}`,
      { method: "DELETE" },
    );
    await refreshNotes();
    setWorkspaceStatus("Note deleted.");
  } catch (error) {
    setWorkspaceStatus(`Failed to delete note: ${error.message}`, true);
  }
}

async function loadSavedViewById(viewId) {
  if (!requireLoggedIn("loading saved views")) {
    return;
  }
  const parsedId = Number(viewId);
  if (!Number.isFinite(parsedId)) {
    setWorkspaceStatus("Choose a saved view first.", true);
    return;
  }

  const view = state.savedViews.find((item) => item.id === parsedId);
  if (!view) {
    setWorkspaceStatus("Saved view not found locally. Refresh list and try again.", true);
    return;
  }

  state.activeSavedAnalysis = view;
  applySavedAnalysisToControls(view);
  selectSavedViewOption(view.id);
  persistActiveSavedViewId(view.id);
  renderShareLinkFromToken(view.share_token);
  await refreshNotes();

  try {
    await loadComparison();
    setWorkspaceStatus(`Loaded saved view: ${view.title}`);
  } catch (error) {
    setWorkspaceStatus(`Loaded view settings but compare failed: ${error.message}`, true);
  }
}

async function updateShareSettings() {
  if (!requireLoggedIn("updating share settings")) {
    elements.shareNotesToggle.checked = false;
    return;
  }

  const analysis = getActiveOwnedAnalysis();
  if (!analysis) {
    if (state.activeSavedAnalysis) {
      elements.shareNotesToggle.checked = Boolean(state.activeSavedAnalysis.share_include_notes);
      setWorkspaceStatus("Only the owner can change note sharing.", true);
    }
    return;
  }

  try {
    const updated = await fetchJson(
      `${getApiBaseUrl()}/workspace/users/${state.user.id}/saved-analyses/${analysis.id}/share-settings`,
      {
        method: "PATCH",
        body: { share_include_notes: Boolean(elements.shareNotesToggle.checked) },
      },
    );
    state.activeSavedAnalysis = updated;
    persistActiveSavedViewId(updated.id);
    await loadSavedViews();
    selectSavedViewOption(updated.id);
    setWorkspaceStatus(
      updated.share_include_notes
        ? "Share links now include notes."
        : "Share links now hide notes.",
    );
  } catch (error) {
    setWorkspaceStatus(`Failed to update sharing settings: ${error.message}`, true);
  }
}

async function loadSharedAnalysisFromQuery() {
  const token = new URLSearchParams(window.location.search).get("share");
  if (!token) {
    return false;
  }

  try {
    const sharedPayload = await fetchJson(`${getApiBaseUrl()}/workspace/shared/${encodeURIComponent(token)}`);
    const saved = sharedPayload.saved_analysis;
    applySavedAnalysisToControls(saved);
    elements.shareNotesToggle.checked = Boolean(saved.share_include_notes);
    state.activeSavedAnalysis = saved;
    state.activeNotes = sharedPayload.notes || [];
    selectSavedViewOption(null);
    renderNotesTable(state.activeNotes);
    renderShareLinkFromToken(saved.share_token);
    const noteShareStatus = sharedPayload.notes_shared
      ? "Notes are visible in this shared link."
      : "Notes are private for this shared link.";
    setWorkspaceStatus(`Loaded shared analysis. ${noteShareStatus}`);
    return true;
  } catch (error) {
    setWorkspaceStatus(`Failed to load shared analysis: ${error.message}`, true);
    return false;
  }
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
    renderInsightsError(`Insights are currently unavailable for this selection: ${error.message}`);
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

  state.activeSavedAnalysis = null;
  state.activeNotes = [];
  renderNotesTable(state.activeNotes);
  elements.shareNotesToggle.checked = false;
  selectSavedViewOption(null);
  setShareLinkText("");

  try {
    await loadComparison();
  } catch (error) {
    setStatus(`Failed to apply preset: ${error.message}`, true);
  }
}

function wireEvents() {
  elements.compareBtn.addEventListener("click", handleRenderClick);
  elements.presetSelect.addEventListener("change", handlePresetChange);
  elements.seriesASearch.addEventListener("input", renderSeriesOptions);
  elements.seriesBSearch.addEventListener("input", renderSeriesOptions);
  elements.seriesA.addEventListener("change", clearWorkspaceSelectionContext);
  elements.seriesB.addEventListener("change", clearWorkspaceSelectionContext);
  elements.eventCategory.addEventListener("change", clearWorkspaceSelectionContext);
  elements.startDate.addEventListener("change", clearWorkspaceSelectionContext);
  elements.endDate.addEventListener("change", clearWorkspaceSelectionContext);

  elements.loginBtn.addEventListener("click", loginUser);
  elements.registerBtn.addEventListener("click", registerUser);
  elements.logoutBtn.addEventListener("click", logoutUser);
  elements.saveViewBtn.addEventListener("click", saveView);
  elements.bookmarkViewBtn.addEventListener("click", toggleBookmark);
  elements.shareViewBtn.addEventListener("click", shareView);
  elements.deleteViewBtn.addEventListener("click", deleteView);
  elements.loadSavedViewBtn.addEventListener("click", () => {
    loadSavedViewById(elements.savedViewsSelect.value);
  });
  elements.savedViewsSelect.addEventListener("change", () => {
    const selectedId = elements.savedViewsSelect.value;
    if (!selectedId) {
      return;
    }
    loadSavedViewById(selectedId);
  });
  elements.shareNotesToggle.addEventListener("change", updateShareSettings);
  elements.saveNoteBtn.addEventListener("click", saveNote);

  elements.passwordInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      loginUser();
    }
  });
}

async function init() {
  setDefaultDates();
  wireEvents();
  updateWorkspaceUserLabel();
  renderSavedViewsOptions();
  renderNotesTable([]);
  elements.shareNotesToggle.checked = false;

  try {
    await loadSeries();
    await loadPresets();
    await loadEventCategories();

    const loadedShare = await loadSharedAnalysisFromQuery();
    if (!loadedShare) {
      if (state.presets.length) {
        elements.presetSelect.value = String(state.presets[0].id);
        applyPreset(state.presets[0]);
      } else {
        applyPreset(null);
      }
    }

    await loadComparison();
  } catch (error) {
    setStatus(`Initialization failed: ${error.message}. Verify the backend is running.`, true);
  }
}

init();
