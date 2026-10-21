"use strict";

// Dark Mode Toggle
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");
const savedTheme = localStorage.getItem("theme") || "light";

document.documentElement.setAttribute("data-theme", savedTheme);
themeIcon.textContent = savedTheme === "dark" ? "☀️" : "🌙";

themeToggle.addEventListener("click", () => {
  const currentTheme = document.documentElement.getAttribute("data-theme");
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("theme", newTheme);
  themeIcon.textContent = newTheme === "dark" ? "☀️" : "🌙";
});

// AQI Calculator and Health Recommendations
function getAQIInfo(pm25) {
  if (pm25 == null || pm25 < 0) return null;
  
  let category, level, icon, recommendations;
  
  if (pm25 <= 12) {
    category = "Good";
    level = "aqi-good";
    icon = "✅";
    recommendations = [
      "Air quality is excellent! Perfect day for outdoor activities",
      "No health precautions needed for any group",
      "Great time for exercise, sports, and outdoor recreation"
    ];
  } else if (pm25 <= 35.4) {
    category = "Moderate";
    level = "aqi-moderate";
    icon = "⚠️";
    recommendations = [
      "Air quality is acceptable for most people",
      "Unusually sensitive people should limit prolonged outdoor exertion",
      "Generally safe for outdoor activities"
    ];
  } else if (pm25 <= 55.4) {
    category = "Unhealthy for Sensitive Groups";
    level = "aqi-unhealthy-sensitive";
    icon = "⚠️";
    recommendations = [
      "Children, elderly, and people with respiratory conditions should reduce outdoor exertion",
      "General public is not likely to be affected",
      "Consider wearing a mask if you're in a sensitive group"
    ];
  } else if (pm25 <= 150.4) {
    category = "Unhealthy";
    level = "aqi-unhealthy";
    icon = "🚨";
    recommendations = [
      "Everyone should reduce prolonged outdoor exertion",
      "Sensitive groups should avoid outdoor activities",
      "Wear N95 masks when going outside",
      "Keep windows closed and use air purifiers indoors"
    ];
  } else if (pm25 <= 250.4) {
    category = "Very Unhealthy";
    level = "aqi-very-unhealthy";
    icon = "🚨";
    recommendations = [
      "Everyone should avoid all outdoor physical activities",
      "Sensitive groups should remain indoors",
      "Use N95 or better masks if you must go outside",
      "Run air purifiers and keep windows sealed"
    ];
  } else {
    category = "Hazardous";
    level = "aqi-hazardous";
    icon = "☠️";
    recommendations = [
      "Health alert! Everyone should stay indoors",
      "Avoid all outdoor activities",
      "Use high-quality air purifiers indoors",
      "Seal windows and doors completely",
      "Wear N99 masks if outdoor exposure is unavoidable"
    ];
  }
  
  return { category, level, icon, recommendations, pm25: pm25.toFixed(1) };
}

function renderHealthWidget(latestPM25) {
  const widget = document.getElementById("health-widget");
  const aqiStatus = document.getElementById("aqi-status");
  const recList = document.getElementById("health-rec-list");
  const healthIcon = document.getElementById("health-icon");
  
  if (!latestPM25 || latestPM25 < 0) {
    widget.style.display = "none";
    return;
  }
  
  const info = getAQIInfo(latestPM25);
  if (!info) {
    widget.style.display = "none";
    return;
  }
  
  widget.style.display = "block";
  healthIcon.textContent = info.icon;
  
  aqiStatus.innerHTML = `
    <div class="aqi-indicator ${info.level}">
      <span>${info.icon}</span>
      <span><strong>${info.category}</strong> - PM2.5: ${info.pm25} µg/m³</span>
    </div>
  `;
  
  recList.innerHTML = "";
  info.recommendations.forEach(rec => {
    const li = document.createElement("li");
    li.textContent = rec;
    recList.appendChild(li);
  });
}

const number = (value, digits = 2) =>
  typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits })
    : "—";

const integer = (value) =>
  typeof value === "number" ? value.toLocaleString() : "—";

const text = (id, value) => {
  const node = document.getElementById(id);
  if (node) node.textContent = value == null ? "" : String(value);
};

const element = (tag, className, content) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = String(content);
  return node;
};

function setStatusBadge(node, status) {
  node.textContent = String(status || "unknown").replaceAll("_", " ");
  node.className = "status-badge";
  if (String(status).includes("warning")) node.classList.add("status-warning");
  if (String(status).includes("fail")) node.classList.add("status-failure");
}

const DAY_MS = 86400000;
const dayNumber = (isoDate) => Math.round(Date.parse(`${isoDate}T00:00:00Z`) / DAY_MS);
const OTHER_SERIES_CLASS = {
  us_consulate_karachi_pm25: "chart-series-consulate",
  urban_unit_karachi_network: "chart-series-network",
};

function renderChart(series, unit, otherSeries = []) {
  const wrap = document.getElementById("chart-wrap");
  wrap.replaceChildren();
  wrap.setAttribute("aria-busy", "false");
  if (!Array.isArray(series) || series.length === 0) {
    wrap.append(element("p", "muted", "No historical observations are available."));
    return;
  }
  const width = 1000;
  const height = 300;
  const margin = { top: 15, right: 18, bottom: 38, left: 58 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const others = (Array.isArray(otherSeries) ? otherSeries : []).filter(
    (item) => Array.isArray(item.points) && item.points.length,
  );
  const allPoints = series.concat(...others.map((item) => item.points));
  const numeric = allPoints.filter((row) => typeof row.value === "number");
  if (!numeric.length) {
    wrap.append(element("p", "muted", "No numeric observations are available to plot."));
    return;
  }
  const maxValue = Math.ceil(Math.max(...numeric.map((row) => row.value)) / 50) * 50;
  const firstDate = allPoints.reduce((min, row) => (row.date < min ? row.date : min), allPoints[0].date);
  const lastDate = allPoints.reduce((max, row) => (row.date > max ? row.date : max), allPoints[0].date);
  const firstDay = dayNumber(firstDate);
  const span = Math.max(dayNumber(lastDate) - firstDay, 1);
  const xAt = (isoDate) => margin.left + ((dayNumber(isoDate) - firstDay) / span) * plotWidth;
  const yAt = (value) => margin.top + (1 - value / maxValue) * plotHeight;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    `Daily PM2.5 from ${firstDate} to ${lastDate}, in ${unit}, one line per source. Missing readings are shown as gaps.`,
  );
  const description = document.createElementNS("http://www.w3.org/2000/svg", "title");
  description.textContent = `Daily PM2.5 readings, ${firstDate} to ${lastDate}; sources are drawn separately and missing records are not interpolated.`;
  svg.append(description);

  // Create tooltip element
  const tooltip = document.createElement("div");
  tooltip.style.position = "absolute";
  tooltip.style.display = "none";
  tooltip.style.padding = "8px 12px";
  tooltip.style.background = "rgba(0, 0, 0, 0.9)";
  tooltip.style.color = "white";
  tooltip.style.borderRadius = "6px";
  tooltip.style.fontSize = "0.875rem";
  tooltip.style.pointerEvents = "none";
  tooltip.style.zIndex = "1000";
  tooltip.style.whiteSpace = "nowrap";
  wrap.appendChild(tooltip);

  for (let tick = 0; tick <= 4; tick += 1) {
    const value = (maxValue / 4) * tick;
    const y = yAt(value);
    const line = document.createElementNS(svg.namespaceURI, "line");
    line.setAttribute("x1", margin.left);
    line.setAttribute("x2", width - margin.right);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("class", "chart-gridline");
    svg.append(line);
    const label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", margin.left - 9);
    label.setAttribute("y", y + 4);
    label.setAttribute("text-anchor", "end");
    label.setAttribute("class", "chart-axis-label");
    label.textContent = number(value, 0);
    svg.append(label);
  }
  const drawLine = (points, className) => {
    let segment = [];
    let previousDay = null;
    const flush = () => {
      if (segment.length >= 2) {
        const path = document.createElementNS(svg.namespaceURI, "polyline");
        path.setAttribute("points", segment.join(" "));
        path.setAttribute("class", className);
        svg.append(path);
      }
      segment = [];
    };
    points.forEach((row) => {
      const day = dayNumber(row.date);
      if (typeof row.value !== "number" || (previousDay !== null && day - previousDay > 1)) flush();
      if (typeof row.value === "number") segment.push(`${xAt(row.date).toFixed(2)},${yAt(row.value).toFixed(2)}`);
      previousDay = day;
    });
    flush();
  };
  for (const item of others) {
    drawLine(item.points, `chart-series ${OTHER_SERIES_CLASS[item.source_id] || "chart-series-other"}`);
  }
  drawLine(series, "chart-series");

  const showTooltip = (event, lines) => {
    const rect = wrap.getBoundingClientRect();
    if (lines) {
      tooltip.replaceChildren();
      lines.forEach((line, index) => {
        if (index) tooltip.append(document.createElement("br"));
        tooltip.append(index === 0 ? element("strong", "", line) : document.createTextNode(line));
      });
    }
    tooltip.style.display = "block";
    tooltip.style.left = (event.clientX - rect.left + 15) + "px";
    tooltip.style.top = (event.clientY - rect.top - 15) + "px";
  };
  for (const item of others) {
    item.points.forEach((row) => {
      if (typeof row.value !== "number") return;
      const circle = document.createElementNS(svg.namespaceURI, "circle");
      circle.setAttribute("cx", xAt(row.date));
      circle.setAttribute("cy", yAt(row.value));
      circle.setAttribute("r", "2.5");
      circle.setAttribute("class", `chart-point-other ${OTHER_SERIES_CLASS[item.source_id] || "chart-series-other"}`);
      circle.addEventListener("mouseenter", (event) =>
        showTooltip(event, [row.date, `PM2.5: ${number(row.value, 1)} µg/m³`, item.label]),
      );
      circle.addEventListener("mousemove", (event) => showTooltip(event, null));
      circle.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
      svg.append(circle);
    });
  }

  // Add interactive points with tooltips
  series.forEach((row) => {
    if (typeof row.value !== "number") return;
    const x = xAt(row.date);
    const y = yAt(row.value);
    const circle = document.createElementNS(svg.namespaceURI, "circle");
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", "3.5");
    circle.setAttribute("class", "chart-point");
    circle.style.cursor = "pointer";
    
    // Get AQI info for color coding
    const aqiInfo = getAQIInfo(row.value);
    if (aqiInfo) {
      const colorMap = {
        "aqi-good": "#10b981",
        "aqi-moderate": "#f59e0b",
        "aqi-unhealthy-sensitive": "#f97316",
        "aqi-unhealthy": "#ef4444",
        "aqi-very-unhealthy": "#9333ea",
        "aqi-hazardous": "#7f1d1d"
      };
      circle.setAttribute("fill", colorMap[aqiInfo.level] || "#0ea5e9");
    }
    
    circle.addEventListener("mouseenter", (e) => {
      const rect = wrap.getBoundingClientRect();
      const aqiInfo = getAQIInfo(row.value);
      tooltip.innerHTML = `
        <strong>${row.date}</strong><br>
        PM2.5: ${number(row.value, 1)} µg/m³<br>
        ${aqiInfo ? `<span style="color: ${aqiInfo.level.includes('good') ? '#34d399' : aqiInfo.level.includes('hazardous') ? '#f87171' : '#fbbf24'}">${aqiInfo.icon} ${aqiInfo.category}</span>` : ''}
      `;
      tooltip.style.display = "block";
      tooltip.style.left = (e.clientX - rect.left + 15) + "px";
      tooltip.style.top = (e.clientY - rect.top - 15) + "px";
    });
    
    circle.addEventListener("mousemove", (e) => {
      const rect = wrap.getBoundingClientRect();
      tooltip.style.left = (e.clientX - rect.left + 15) + "px";
      tooltip.style.top = (e.clientY - rect.top - 15) + "px";
    });
    
    circle.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
    });
    
    svg.append(circle);
  });
  
  series.forEach((row) => {
    if (row.value !== null) return;
    const x = xAt(row.date);
    const marker = document.createElementNS(svg.namespaceURI, "line");
    marker.setAttribute("x1", x);
    marker.setAttribute("x2", x);
    marker.setAttribute("y1", margin.top);
    marker.setAttribute("y2", height - margin.bottom);
    marker.setAttribute("stroke", "#d4a45e");
    marker.setAttribute("stroke-width", "1");
    marker.setAttribute("stroke-dasharray", "2 4");
    marker.setAttribute("opacity", ".45");
    const title = document.createElementNS(svg.namespaceURI, "title");
    title.textContent = `No PM2.5 value reported on ${row.date}`;
    marker.append(title);
    svg.append(marker);
  });
  const yearLabels = [];
  for (let year = Number(firstDate.slice(0, 4)); year <= Number(lastDate.slice(0, 4)); year += 1) {
    const start = `${year}-01-01` < firstDate ? firstDate : `${year}-01-01`;
    yearLabels.push({ year: String(year), x: xAt(start) });
  }
  const maxLabels = 9;
  const stride = Math.max(1, Math.ceil(yearLabels.length / maxLabels));
  yearLabels.filter((_, index) => index % stride === 0 || index === yearLabels.length - 1).forEach(({ year, x }) => {
    const label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", x);
    label.setAttribute("y", height - 11);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "chart-axis-label");
    label.textContent = year;
    svg.append(label);
  });
  wrap.append(svg);
  const legend = element("div", "chart-legend");
  const legendItem = (className, label) => {
    const item = element("span", "chart-legend-item");
    item.append(element("span", `chart-legend-swatch ${className}`), document.createTextNode(label));
    legend.append(item);
  };
  legendItem("chart-series-paqi", "PAQI Karachi daily (published, ends " + series[series.length - 1].date + ")");
  for (const item of others) legendItem(OTHER_SERIES_CLASS[item.source_id] || "chart-series-other", item.label);
  wrap.append(legend);
}

function renderYearTable(rows) {
  const body = document.getElementById("yearly-body");
  body.replaceChildren();
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = element("td", "", "No yearly summary is available.");
    td.colSpan = 6;
    tr.append(td);
    body.append(tr);
    return;
  }
  rows.forEach((year) => {
    const tr = document.createElement("tr");
    [
      year.year,
      integer(year.n),
      integer(year.missing),
      number(year.mean),
      number(year.median),
      `${number(year.minimum)}–${number(year.maximum)}`,
    ].forEach((value) => tr.append(element("td", "", value)));
    body.append(tr);
  });
}

function renderQuality(quality) {
  setStatusBadge(document.getElementById("quality-badge"), quality.pipeline_status);
  text("quality-run-id", quality.run_id || "Unavailable");
  text("quality-run-time", quality.checked_at_utc || "Unavailable");
  text("quality-count-scope", quality.count_scope || "current run only");
  const counts = quality.counts || {};
  const countWrap = document.getElementById("quality-counts");
  countWrap.replaceChildren();
  [
    ["passed_checks", "Passed checks"],
    ["warning_checks", "Warning checks"],
    ["failed_checks", "Failed checks"],
    ["fixes", "FIX decisions"],
    ["fills_not_applied", "Fills not applied"],
    ["flags", "FLAG decisions"],
  ].forEach(([key, label]) => {
    const card = element("div", "quality-count");
    card.append(element("strong", "", integer(counts[key] || 0)));
    card.append(element("span", "", label));
    countWrap.append(card);
  });
  const list = document.getElementById("warning-list");
  list.replaceChildren();
  const warningChecks = quality.warning_checks || [];
  if (!warningChecks.length) {
    list.append(element("li", "", "No warning checks are recorded in the latest quality report."));
  } else {
    warningChecks.forEach((check) => {
      const item = element("li", "");
      item.append(element("strong", "", check.name.replaceAll("_", " ")));
      item.append(document.createTextNode(check.detail || check.status));
      list.append(item);
    });
  }
  text("methodology-warning", quality.unresolved_methodology);
  text(
    "second-source-warning",
    `Second-source compliance: ${String(quality.two_source_compliance || "not_established").replaceAll("_", " ")}. Quality log is append-only history; counts above are for the latest run only.`,
  );
}

function metricRow(label, modelValue, baselineValue) {
  const row = element("div", "score-row");
  row.append(element("span", "", label));
  row.append(element("strong", "", number(modelValue, 4)));
  row.append(element("strong", "", number(baselineValue, 4)));
  return row;
}

function renderForecast(forecast) {
  const wrap = document.getElementById("forecast-cards");
  wrap.replaceChildren();
  const splits = [
    ["Validation", forecast.validation],
    ["Held-out test", forecast.test],
  ];
  splits.forEach(([title, split]) => {
    const card = element("article", "panel forecast-card");
    card.append(element("h3", "", title));
    const dates = split.dates || {};
    card.append(element("p", "forecast-dates", `${dates.start || "—"} to ${dates.end || "—"}`));
    const heading = element("div", "score-row score-head");
    ["Metric", "Linear model", "Persistence*"].forEach((label) => heading.append(element("span", "", label)));
    card.append(heading);
    const model = split.linear_model || {};
    const baseline = split.persistence_on_model_matched_targets || {};
    card.append(metricRow("MAE (µg/m³)", model.mae, baseline.mae));
    card.append(metricRow("RMSE (µg/m³)", model.rmse, baseline.rmse));
    const pair = split.paired_model_minus_persistence || {};
    card.append(
      element(
        "p",
        "delta",
        `Matched n=${integer(pair.n)} · model − persistence: ΔMAE ${number(pair.mae_difference, 4)}, ΔRMSE ${number(pair.rmse_difference, 4)} µg/m³`,
      ),
    );
    wrap.append(card);
  });
  text(
    "forecast-caveat",
    "* Persistence is evaluated on the same dates as the linear model. Negative deltas favor the model. The test improvement is modest and descriptive; no statistical significance is claimed. Backtesting ends 2024-12-31 and is not an operational/current forecast.",
  );
}

function setSafeLink(node, href, label) {
  try {
    const parsed = new URL(href);
    if (parsed.protocol !== "https:") throw new Error("Only HTTPS links are allowed.");
    node.href = parsed.href;
    node.textContent = label;
  } catch {
    node.removeAttribute("href");
    node.textContent = `${label} (link unavailable)`;
  }
}

function freshnessClass(state) {
  if (state === "fresh") return "status-badge";
  if (state === "delayed") return "status-badge status-warning";
  return "status-badge status-failure";
}

function renderLive(live) {
  const badge = document.getElementById("live-badge");
  const primaryWrap = document.getElementById("live-primary");
  const grid = document.getElementById("live-grid");
  if (!badge || !primaryWrap || !grid) return;

  text("live-disclaimer", live.coverage_disclaimer || "Point sensor readings only.");
  const available = live.available_pm25_sensor_count || 0;
  badge.textContent =
    live.status === "ok"
      ? `${available} sensor${available === 1 ? "" : "s"} with PM2.5`
      : "Live feed unavailable";
  badge.className = live.status === "ok" ? "status-badge" : "status-badge status-warning";

  primaryWrap.replaceChildren();
  const primary = live.primary_sensor;
  if (primary && primary.pm25_ug_m3 != null) {
    const title = element("h3", "", primary.location_name || primary.configured_label || "Primary sensor");
    const value = element("p", "live-value", `${number(primary.pm25_ug_m3, 1)} µg/m³ PM2.5`);
    const meta = element(
      "p",
      "muted",
      `Observed ${primary.observation_time_pkt || primary.observation_time_utc || "—"} · fetched ${primary.fetched_at_pkt || primary.fetched_at_utc || "—"} · ${String(primary.freshness || "unavailable")}`,
    );
    const area = element("p", "muted", `${primary.area || "Karachi"} · AirGradient id ${primary.location_id}`);
    const status = element("span", freshnessClass(primary.freshness), String(primary.freshness || "unavailable"));
    primaryWrap.append(status, title, value, area, meta);
  } else {
    primaryWrap.append(
      element(
        "p",
        "muted",
        live.error
          ? `Live sensors unavailable: ${live.error}`
          : "No verified public PM2.5 reading is available right now. Historical evidence below remains usable.",
      ),
    );
  }

  grid.replaceChildren();
  (live.sensors || []).forEach((sensor) => {
    const card = element("article", "panel live-card");
    card.append(element("span", freshnessClass(sensor.freshness), String(sensor.freshness || "unavailable")));
    card.append(element("h3", "", sensor.location_name || sensor.configured_label || `Sensor ${sensor.location_id}`));
    card.append(
      element(
        "p",
        "live-card-value",
        sensor.pm25_ug_m3 == null ? "PM2.5 unavailable" : `${number(sensor.pm25_ug_m3, 1)} µg/m³`,
      ),
    );
    const extras = [];
    if (sensor.temperature_c != null) extras.push(`Temp ${number(sensor.temperature_c, 1)} °C`);
    if (sensor.relative_humidity_pct != null) extras.push(`RH ${number(sensor.relative_humidity_pct, 0)}%`);
    if (sensor.pm1_ug_m3 != null) extras.push(`PM1 ${number(sensor.pm1_ug_m3, 1)}`);
    card.append(element("p", "muted", extras.join(" · ") || sensor.area || ""));
    card.append(
      element(
        "p",
        "muted",
        sensor.error
          ? `Fetch issue: ${sensor.error}`
          : `Observed ${sensor.observation_time_pkt || "—"}`,
      ),
    );
    grid.append(card);
  });

  const orangi = (live.unavailable_targets || [])
    .map((item) => `${item.label}: ${item.status}. ${item.notes || ""}`)
    .join(" ");
  text("live-orangi-note", orangi);
  text(
    "live-attribution",
    live.provider
      ? `${live.provider.attribution || ""} ${live.provider.license_note || ""}`.trim()
      : "",
  );
}

function renderHealth(health) {
  if (!health) return;
  text("health-title", health.title || "Understanding PM2.5");
  text("health-summary", health.summary || "");
  text("health-caveat", health.caveat || "");
  text("health-reference", health.reference || "");
}

function renderHowItWorks(steps) {
  const list = document.getElementById("how-it-works");
  if (!list) return;
  list.replaceChildren();
  (steps || []).forEach((step, index) => {
    const item = element("li", "");
    item.append(element("strong", "", `${index + 1}.`));
    item.append(document.createTextNode(` ${step}`));
    list.append(item);
  });
}

function renderDashboard(data) {
  const overview = data.overview;
  text("date-range", `${overview.start_date} – ${overview.end_date}`);
  text("dated-count", integer(overview.dated_records));
  text("numeric-count", integer(overview.numeric_readings));
  text("missing-count", integer(overview.missing_readings));
  const freshness = overview.freshness;
  const latest = overview.latest_any_source;
  text("last-observation", latest ? latest.date : freshness.last_observation_date);
  text(
    "freshness-label",
    latest
      ? `Newest daily reading ${latest.date} (${latest.source}, ${integer(latest.age_days)} days old). The published PAQI series ends ${freshness.last_observation_date}.`
      : `Historical last observation ${freshness.last_observation_date} · ${integer(freshness.age_days)} days old. Live sensors are a separate feed below.`,
  );
  text(
    "stale-detail",
    latest
      ? `${latest.source}. PAQI published file ends ${freshness.last_observation_date}.`
      : freshness.is_stale
        ? `Historical series exceeds the ${freshness.warning_threshold_days}-day warning threshold.`
        : `Historical series within the ${freshness.warning_threshold_days}-day warning threshold.`,
  );
  const pipeline = overview.pipeline;
  setStatusBadge(document.getElementById("pipeline-badge"), pipeline.latest_status);
  const lastSuccess = pipeline.last_successful_run;
  text(
    "last-run",
    lastSuccess
      ? lastSuccess.finished_at_utc || lastSuccess.run_id || "Recorded successful run"
      : "No prior successful run is separately persisted",
  );
  text("run-detail", `${pipeline.success_history_note} Latest run ID: ${pipeline.latest_run_id || "unavailable"}.`);
  
  // Render health widget with latest PM2.5
  const latestPM25 = latest
    ? latest.value
    : data.historical.series.length > 0
      ? data.historical.series[data.historical.series.length - 1].value
      : null;
  renderHealthWidget(latestPM25);
  
  // Render stats cards and heatmap
  renderStatsCards(data.historical.series);
  renderCalendarHeatmap(data.historical.series);
  
  renderLive(data.live || { status: "unavailable", sensors: [] });
  const otherSeries = data.historical.other_series || [];
  renderChart(data.historical.series, data.historical.unit, otherSeries);
  const missingDates = data.historical.missing_dates || [];
  const otherCounts = otherSeries
    .map((item) => `${item.points.filter((point) => typeof point.value === "number").length.toLocaleString()} ${item.label.split(" (")[0]}`)
    .join(" · ");
  text(
    "chart-caption",
    `${data.historical.series.length.toLocaleString()} PAQI daily records · ${missingDates.length} blank PAQI readings shown as gaps${missingDates.length ? ` (${missingDates.join(", ")})` : ""}${otherCounts ? ` · ${otherCounts} daily values` : ""}. Days that fail a source's completeness rule are left as gaps.`,
  );
  renderYearTable(data.historical.yearly_summary || []);
  renderQuality(data.quality);
  renderForecast(data.forecast);
  renderHealth(data.health_guidance);
  renderHowItWorks(data.how_it_works);
  text("source-name", data.source.name || "PAQI Karachi daily PM2.5 dataset");
  text("source-publisher", data.source.publisher);
  setSafeLink(document.getElementById("source-link"), data.source.url, "Open pinned dataset record ↗");
  setSafeLink(document.getElementById("license-link"), data.source.license_url, "CC BY 4.0 licence ↗");
  text("source-license", data.source.license_summary);
  text("attribution", data.source.attribution);
  renderSecondSource(data.warehouse || {});
  text("page-generated", `Dashboard data assembled ${data.generated_at_utc}`);
  document.getElementById("dashboard-content").hidden = false;
  document.getElementById("loading").hidden = true;
  
  // Setup export functionality
  setupExportButtons(data.historical.series);
}

function renderInsight(result) {
  const panel = document.getElementById("answer-panel");
  panel.replaceChildren();
  const status = element("span", `answer-status ${result.status}`);
  status.textContent = result.status.replaceAll("_", " ");
  panel.append(status);
  const explanation = result.explanation || {};
  if (explanation.used) {
    panel.append(element("h3", "", "Plain-language explanation"));
    const copy = element("p", "answer-copy", explanation.text);
    if (explanation.language === "ur") {
      copy.setAttribute("lang", "ur");
      copy.setAttribute("dir", "rtl");
    }
    panel.append(copy);
    panel.append(element("p", "answer-meta", `AI-generated by ${explanation.model}; every number was checked against the cited evidence [E1…].`));
  }
  panel.append(element("h3", "", explanation.used ? "Verified answer" : "Evidence-grounded answer"));
  panel.append(element("p", "answer-copy", result.answer));
  panel.append(element("p", "answer-meta", `Data as of ${result.data_as_of} · Generated ${result.generated_at}`));
  if (result.evidence && result.evidence.length) {
    panel.append(element("h3", "", "Evidence references"));
    const list = element("ul", "evidence-list");
    result.evidence.forEach((item) => {
      const entry = element("li", "");
      entry.append(element("strong", "", `[E${list.children.length + 1}] `));
      entry.append(element("code", "", item.source_file));
      if (item.locator) entry.append(document.createTextNode(` · ${item.locator}`));
      if (item.date_range) entry.append(document.createTextNode(` · ${item.date_range.start} to ${item.date_range.end}`));
      const rowIds = item.row_ids || item.sample_row_ids || [];
      if (rowIds.length) {
        const ids = element("div", "muted", `Row IDs: ${rowIds.join(", ")}`);
        entry.append(ids);
      }
      list.append(entry);
    });
    panel.append(list);
  }
  if (result.limitations && result.limitations.length) {
    panel.append(element("h3", "", "Limitations"));
    const list = element("ul", "limitations-list");
    result.limitations.forEach((limitation) => list.append(element("li", "", limitation)));
    panel.append(list);
  }
}

function renderSecondSource(warehouse) {
  const second = (warehouse.sources || []).find((item) => item.source_id === "us_consulate_karachi_pm25");
  if (!second) {
    text("second-source-publisher", "Second-source warehouse report is not available for this build.");
    return;
  }
  text("second-source-publisher", `${second.publisher}. ${number(second.gold_rows, 0)} hourly gold rows, latest ${second.latest_observation}.`);
  setSafeLink(document.getElementById("second-source-link"), second.access, "Open OpenAQ location record ↗");
  text("second-source-license", `Licence: ${second.license}. Quality status: ${String(second.status).replaceAll("_", " ")}.`);
  const cross = warehouse.cross_source || {};
  text(
    "cross-source-summary",
    cross.paired_days
      ? `Agreement with PAQI on ${number(cross.paired_days, 0)} shared days (${cross.first_paired_date} → ${cross.last_paired_date}): Pearson r = ${cross.pearson_r}, mean difference ${cross.mean_difference_paqi_minus_consulate} µg/m³ (PAQI − Consulate), ${cross.large_disagreement_days} days flagged for large disagreement.`
      : "Cross-source agreement was not computed in this build.",
  );
  const network = (warehouse.sources || []).find((item) => item.source_id === "urban_unit_karachi_airgradient_pm25");
  if (!network) return;
  text("network-source-publisher", `${network.publisher}. ${number(network.gold_rows, 0)} hourly gold rows (${network.resolution}).`);
  setSafeLink(document.getElementById("network-source-link"), network.access, "Open OpenAQ explorer ↗");
  text("network-source-license", `Licence: ${network.license}. Quality status: ${String(network.status).replaceAll("_", " ")}.`);
  text(
    "network-source-freshness",
    `Latest hour in warehouse: ${network.latest_observation} (${number(network.latest_age_hours, 1)} h old when the pipeline last ran). Warehouse total: ${number(warehouse.total_gold_rows, 0)} gold rows across ${(warehouse.sources || []).length} sources.`,
  );
}

async function loadDashboard() {
  try {
    const response = await fetch("/api/dashboard", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Dashboard data service returned HTTP ${response.status}.`);
    renderDashboard(await response.json());
  } catch (error) {
    document.getElementById("loading").hidden = true;
    const box = document.getElementById("error");
    box.textContent = `Dashboard data could not be loaded. ${error.message}`;
    box.hidden = false;
  }
}

// Export Functionality
function setupExportButtons(series) {
  const exportCsvBtn = document.getElementById("export-csv");
  const exportChartBtn = document.getElementById("export-chart");
  
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener("click", () => exportToCSV(series));
  }
  
  if (exportChartBtn) {
    exportChartBtn.addEventListener("click", () => exportChartAsImage());
  }
}

function exportToCSV(series) {
  if (!series || series.length === 0) {
    alert("No data available to export");
    return;
  }
  
  // Create CSV content
  let csvContent = "Date,PM2.5 (µg/m³)\n";
  series.forEach(row => {
    const value = row.value !== null && row.value !== undefined ? row.value : "";
    csvContent += `${row.date},${value}\n`;
  });
  
  // Create download link
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `karachi-air-quality-${new Date().toISOString().split('T')[0]}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function exportChartAsImage() {
  const svg = document.querySelector("#chart-wrap svg");
  if (!svg) {
    alert("No chart available to export");
    return;
  }
  
  // Get SVG data
  const svgData = new XMLSerializer().serializeToString(svg);
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const img = new Image();
  
  // Set canvas size
  canvas.width = 1200;
  canvas.height = 400;
  
  // Fill white background
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  img.onload = function() {
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(blob => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `karachi-pm25-chart-${new Date().toISOString().split('T')[0]}.png`;
      link.click();
      URL.revokeObjectURL(url);
    });
  };
  
  const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
  const svgUrl = URL.createObjectURL(svgBlob);
  img.src = svgUrl;
}

const answerLanguage = () => document.getElementById("answer-language")?.value || "en";

async function askQuestion(question) {
  const button = document.getElementById("ask-button");
  const panel = document.getElementById("answer-panel");
  const field = document.getElementById("question");
  if (!question) return;
  field.value = question;
  button.disabled = true;
  button.textContent = "Retrieving evidence…";
  panel.setAttribute("aria-busy", "true");
  panel.replaceChildren(element("p", "muted", "The local Insight Agent is checking the project evidence…"));
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ question, language: answerLanguage() }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Insight Agent returned HTTP ${response.status}.`);
    renderInsight(result);
  } catch (error) {
    panel.replaceChildren(element("p", "error-card", `Could not retrieve an answer: ${error.message}`));
  } finally {
    button.disabled = false;
    button.innerHTML = 'Ask with evidence <span aria-hidden="true">→</span>';
    panel.setAttribute("aria-busy", "false");
  }
}

document.getElementById("question-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await askQuestion(document.getElementById("question").value.trim());
});

document.querySelectorAll(".chip-button").forEach((button) => {
  button.addEventListener("click", () => {
    const question = button.getAttribute("data-question");
    if (question) askQuestion(question);
  });
});

// Chat Widget Functionality
const chatWidgetButton = document.getElementById("chat-widget-button");
const chatWidgetModal = document.getElementById("chat-widget-modal");
const chatWidgetClose = document.getElementById("chat-widget-close");
const chatWidgetContent = document.getElementById("chat-widget-content");
const chatWidgetInput = document.getElementById("chat-widget-input");
const chatWidgetSend = document.getElementById("chat-widget-send");

let chatHistory = [];

function toggleChatWidget() {
  const isOpen = chatWidgetModal.classList.contains("open");
  if (isOpen) {
    chatWidgetModal.classList.remove("open");
    chatWidgetButton.classList.remove("active");
    chatWidgetButton.innerHTML = "💬";
  } else {
    chatWidgetModal.classList.add("open");
    chatWidgetButton.classList.add("active");
    chatWidgetButton.innerHTML = "×";
    chatWidgetInput.focus();
  }
}

function addChatMessage(role, content, meta = null) {
  const messageDiv = element("div", `chat-message ${role}`);
  const avatar = element("div", "chat-avatar", role === "user" ? "You" : "AI");
  const bubble = element("div", "chat-bubble");
  
  if (typeof content === "string") {
    bubble.textContent = content;
  } else {
    bubble.appendChild(content);
  }
  
  if (meta) {
    const metaDiv = element("div", "chat-bubble-meta", meta);
    bubble.appendChild(metaDiv);
  }
  
  messageDiv.appendChild(avatar);
  messageDiv.appendChild(bubble);
  
  if (chatHistory.length === 0) {
    chatWidgetContent.innerHTML = "";
  }
  
  chatWidgetContent.appendChild(messageDiv);
  chatWidgetContent.scrollTop = chatWidgetContent.scrollHeight;
  
  chatHistory.push({ role, content, meta });
}

async function sendChatMessage(question) {
  if (!question.trim()) return;
  
  addChatMessage("user", question);
  chatWidgetInput.value = "";
  chatWidgetSend.disabled = true;
  
  const thinkingDiv = element("div", "");
  thinkingDiv.innerHTML = "Analyzing evidence...";
  addChatMessage("agent", thinkingDiv);
  
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ question, language: answerLanguage() }),
    });
    const result = await response.json();
    
    chatWidgetContent.removeChild(chatWidgetContent.lastChild);
    chatHistory.pop();
    
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    
    const answerContent = element("div", "");
    const statusBadge = element("span", `answer-status ${result.status}`, result.status.replaceAll("_", " "));
    answerContent.appendChild(statusBadge);
    answerContent.appendChild(document.createElement("br"));
    if (result.explanation && result.explanation.used) {
      const explained = element("p", "", result.explanation.text);
      if (result.explanation.language === "ur") {
        explained.setAttribute("lang", "ur");
        explained.setAttribute("dir", "rtl");
      }
      answerContent.appendChild(explained);
      answerContent.appendChild(element("small", "muted", `AI explanation (${result.explanation.model}), numbers checked against evidence. Verified answer:`));
      answerContent.appendChild(document.createElement("br"));
    }
    answerContent.appendChild(document.createTextNode(result.answer));
    
    if (result.evidence && result.evidence.length) {
      const evidenceTitle = element("strong", "", "Evidence: ");
      answerContent.appendChild(document.createElement("br"));
      answerContent.appendChild(document.createElement("br"));
      answerContent.appendChild(evidenceTitle);
      answerContent.appendChild(document.createTextNode(result.evidence.map(e => e.source_file).join(", ")));
    }
    
    const meta = `${result.data_as_of} · ${result.generated_at}`;
    addChatMessage("agent", answerContent, meta);
    
  } catch (error) {
    chatWidgetContent.removeChild(chatWidgetContent.lastChild);
    chatHistory.pop();
    addChatMessage("agent", `Error: ${error.message}`);
  } finally {
    chatWidgetSend.disabled = false;
  }
}

chatWidgetButton.addEventListener("click", toggleChatWidget);
chatWidgetClose.addEventListener("click", toggleChatWidget);

chatWidgetSend.addEventListener("click", () => {
  sendChatMessage(chatWidgetInput.value.trim());
});

chatWidgetInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage(chatWidgetInput.value.trim());
  }
});

document.querySelectorAll(".chat-widget-example-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const question = button.getAttribute("data-question");
    if (question) sendChatMessage(question);
  });
});

// Keyboard Shortcuts
document.addEventListener("keydown", (e) => {
  // Don't trigger if user is typing in an input
  if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
  
  const key = e.key.toLowerCase();
  
  if (key === "d") {
    e.preventDefault();
    document.getElementById("theme-toggle").click();
  } else if (key === "e") {
    e.preventDefault();
    const exportBtn = document.getElementById("export-csv");
    if (exportBtn) exportBtn.click();
  } else if (key === "/") {
    e.preventDefault();
    const chatBtn = document.getElementById("chat-widget-button");
    if (chatBtn) chatBtn.click();
  } else if (key === "s") {
    e.preventDefault();
    const shareBtn = document.getElementById("share-twitter");
    if (shareBtn) shareBtn.click();
  } else if (key === "?" || (e.shiftKey && key === "/")) {
    e.preventDefault();
    toggleShortcutsModal();
  } else if (key === "escape") {
    hideShortcutsModal();
  }
});

function toggleShortcutsModal() {
  const modal = document.getElementById("shortcuts-modal");
  const overlay = document.getElementById("shortcuts-overlay");
  const isVisible = modal.classList.contains("visible");
  
  if (isVisible) {
    modal.classList.remove("visible");
    overlay.classList.remove("visible");
  } else {
    modal.classList.add("visible");
    overlay.classList.add("visible");
  }
}

function hideShortcutsModal() {
  document.getElementById("shortcuts-modal").classList.remove("visible");
  document.getElementById("shortcuts-overlay").classList.remove("visible");
}

document.getElementById("shortcuts-overlay")?.addEventListener("click", hideShortcutsModal);

// Stats Summary Cards
function renderStatsCards(series) {
  if (!series || series.length === 0) return;
  
  // Get the latest year from data
  const latestYear = series.length > 0 ? series[series.length - 1].date.substring(0, 4) : "2024";
  const currentYearData = series.filter(row => row.date.startsWith(latestYear) && typeof row.value === "number");
  
  if (currentYearData.length === 0) {
    // Use all available data if current year has none
    const allNumeric = series.filter(row => typeof row.value === "number");
    if (allNumeric.length === 0) return;
    
    // Use last 60 days for trend
    const last30 = allNumeric.slice(-30);
    const prev30 = allNumeric.slice(-60, -30);
    
    if (last30.length > 0 && prev30.length > 0) {
      const last30Avg = last30.reduce((sum, r) => sum + r.value, 0) / last30.length;
      const prev30Avg = prev30.reduce((sum, r) => sum + r.value, 0) / prev30.length;
      const diff = last30Avg - prev30Avg;
      const pct = ((diff / prev30Avg) * 100).toFixed(1);
      
      text("trend-value", diff < 0 ? "Improving ✓" : "Worsening ✗");
      text("trend-meta", `${Math.abs(diff).toFixed(1)} µg/m³ (${Math.abs(pct)}%) vs previous period`);
    }
    
    const bestDay = allNumeric.reduce((min, curr) => curr.value < min.value ? curr : min);
    text("best-day-value", `${bestDay.date}`);
    text("best-day-meta", `${number(bestDay.value, 1)} µg/m³ - ${getAQIInfo(bestDay.value)?.category || "Good"}`);
    
    const worstDay = allNumeric.reduce((max, curr) => curr.value > max.value ? curr : max);
    text("worst-day-value", `${worstDay.date}`);
    text("worst-day-meta", `${number(worstDay.value, 1)} µg/m³ - ${getAQIInfo(worstDay.value)?.category || "Hazardous"}`);
    
    const unhealthyDays = allNumeric.filter(r => r.value > 55.4).length;
    const pctUnhealthy = ((unhealthyDays / allNumeric.length) * 100).toFixed(1);
    text("unhealthy-days-value", `${unhealthyDays} days`);
    text("unhealthy-days-meta", `${pctUnhealthy}% of records had unhealthy air`);
    
    // Update card titles
    const cards = document.querySelectorAll(".stats-card h4");
    if (cards[1]) cards[1].textContent = "Best Day (All Time)";
    if (cards[2]) cards[2].textContent = "Worst Day (All Time)";
    
    return;
  }
  
  // Calculate trend (last 30 days vs previous 30 days) for current year
  const last30 = currentYearData.slice(-30).filter(r => typeof r.value === "number");
  const prev30 = currentYearData.slice(-60, -30).filter(r => typeof r.value === "number");
  
  if (last30.length > 0 && prev30.length > 0) {
    const last30Avg = last30.reduce((sum, r) => sum + r.value, 0) / last30.length;
    const prev30Avg = prev30.reduce((sum, r) => sum + r.value, 0) / prev30.length;
    const diff = last30Avg - prev30Avg;
    const pct = ((diff / prev30Avg) * 100).toFixed(1);
    
    text("trend-value", diff < 0 ? "Improving ✓" : "Worsening ✗");
    text("trend-meta", `${Math.abs(diff).toFixed(1)} µg/m³ (${Math.abs(pct)}%) vs last month`);
  }
  
  // Best day in current year
  const bestDay = currentYearData.reduce((min, curr) => 
    curr.value < min.value ? curr : min
  );
  text("best-day-value", `${bestDay.date}`);
  text("best-day-meta", `${number(bestDay.value, 1)} µg/m³ - ${getAQIInfo(bestDay.value)?.category || "Good"}`);
  
  // Worst day in current year
  const worstDay = currentYearData.reduce((max, curr) => 
    curr.value > max.value ? curr : max
  );
  text("worst-day-value", `${worstDay.date}`);
  text("worst-day-meta", `${number(worstDay.value, 1)} µg/m³ - ${getAQIInfo(worstDay.value)?.category || "Hazardous"}`);
  
  // Unhealthy days (PM2.5 > 55.4) in current year
  const unhealthyDays = currentYearData.filter(r => r.value > 55.4).length;
  const pctUnhealthy = ((unhealthyDays / currentYearData.length) * 100).toFixed(1);
  text("unhealthy-days-value", `${unhealthyDays} days`);
  text("unhealthy-days-meta", `${pctUnhealthy}% of ${latestYear} had unhealthy air`);
  
  // Update card titles to show the actual year
  const cards = document.querySelectorAll(".stats-card h4");
  if (cards[1]) cards[1].textContent = `Best Day (${latestYear})`;
  if (cards[2]) cards[2].textContent = `Worst Day (${latestYear})`;
}

// Calendar Heatmap
function renderCalendarHeatmap(series) {
  const container = document.getElementById("calendar-heatmap");
  if (!container || !series || series.length === 0) return;
  
  container.innerHTML = "";
  
  // Get the latest year from data
  const latestYear = series.length > 0 ? series[series.length - 1].date.substring(0, 4) : "2024";
  
  // Update the heading
  const heatmapHeading = document.querySelector(".heatmap-panel h3");
  if (heatmapHeading) {
    heatmapHeading.textContent = `Air Quality Calendar (${latestYear})`;
  }
  
  // Filter data for the latest year
  const yearData = series.filter(row => row.date.startsWith(latestYear));
  
  if (yearData.length === 0) return;
  
  // Create map of dates to values
  const dateMap = {};
  yearData.forEach(row => {
    dateMap[row.date] = row.value;
  });
  
  // Generate all days of the year
  const startDate = new Date(`${latestYear}-01-01`);
  const endDate = new Date(`${latestYear}-12-31`);
  
  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split('T')[0];
    const value = dateMap[dateStr];
    
    const cell = document.createElement("div");
    cell.className = "heatmap-cell";
    
    if (value == null) {
      cell.setAttribute("data-level", "0");
      cell.title = `${dateStr}: No data`;
    } else {
      const aqi = getAQIInfo(value);
      let level = 1;
      if (value <= 12) level = 1;
      else if (value <= 35.4) level = 2;
      else if (value <= 55.4) level = 3;
      else if (value <= 150.4) level = 4;
      else if (value <= 250.4) level = 5;
      else level = 6;
      
      cell.setAttribute("data-level", level);
      cell.title = `${dateStr}: ${number(value, 1)} µg/m³ - ${aqi?.category || ""}`;
    }
    
    container.appendChild(cell);
  }
}

// Share to Twitter
function shareToTwitter() {
  const latestData = document.getElementById("last-observation")?.textContent || "latest";
  const aqiStatus = document.querySelector("#aqi-status")?.textContent || "air quality data";
  
  const text = `Check out Karachi's Air Quality Dashboard! Latest data: ${latestData}. Real-time PM2.5 monitoring, health recommendations, and forecasts. #AirQuality #Pakistan #Karachi`;
  const url = window.location.href;
  
  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
  window.open(twitterUrl, '_blank', 'width=550,height=420');
}

document.getElementById("share-twitter")?.addEventListener("click", shareToTwitter);

loadDashboard();
