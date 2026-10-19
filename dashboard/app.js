"use strict";

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

function renderChart(series, unit) {
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
  const numeric = series.filter((row) => typeof row.value === "number");
  if (!numeric.length) {
    wrap.append(element("p", "muted", "No numeric observations are available to plot."));
    return;
  }
  const maxValue = Math.ceil(Math.max(...numeric.map((row) => row.value)) / 50) * 50;
  const xAt = (index) => margin.left + (index / Math.max(series.length - 1, 1)) * plotWidth;
  const yAt = (value) => margin.top + (1 - value / maxValue) * plotHeight;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    `Daily historical PM2.5 series from ${series[0].date} to ${series[series.length - 1].date}, in ${unit}. Missing readings are shown as gaps.`,
  );
  const description = document.createElementNS("http://www.w3.org/2000/svg", "title");
  description.textContent = `Historical daily PM2.5 readings, ${series[0].date} to ${series[series.length - 1].date}; missing records are not interpolated.`;
  svg.append(description);

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
  const segments = [];
  let segment = [];
  series.forEach((row, index) => {
    if (typeof row.value === "number") {
      segment.push(`${xAt(index).toFixed(2)},${yAt(row.value).toFixed(2)}`);
    } else if (segment.length) {
      segments.push(segment);
      segment = [];
    }
  });
  if (segment.length) segments.push(segment);
  for (const points of segments) {
    if (points.length < 2) continue;
    const path = document.createElementNS(svg.namespaceURI, "polyline");
    path.setAttribute("points", points.join(" "));
    path.setAttribute("class", "chart-series");
    svg.append(path);
  }
  series.forEach((row, index) => {
    if (row.value !== null) return;
    const x = xAt(index);
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
  series.forEach((row, index) => {
    if (index === 0 || row.date.slice(0, 4) !== series[index - 1].date.slice(0, 4)) {
      yearLabels.push({ year: row.date.slice(0, 4), x: xAt(index) });
    }
  });
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

function renderDashboard(data) {
  const overview = data.overview;
  text("date-range", `${overview.start_date} – ${overview.end_date}`);
  text("dated-count", integer(overview.dated_records));
  text("numeric-count", integer(overview.numeric_readings));
  text("missing-count", integer(overview.missing_readings));
  text("last-observation", overview.freshness.last_observation_date);
  const freshness = overview.freshness;
  text(
    "freshness-label",
    `Last observation ${freshness.last_observation_date} · ${integer(freshness.age_days)} days old. Historical data only.`,
  );
  text(
    "stale-detail",
    freshness.is_stale
      ? `Stale: exceeds the ${freshness.warning_threshold_days}-day warning threshold.`
      : `Within the ${freshness.warning_threshold_days}-day warning threshold.`,
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
  renderChart(data.historical.series, data.historical.unit);
  const missingDates = data.historical.missing_dates || [];
  text(
    "chart-caption",
    `${data.historical.series.length.toLocaleString()} daily records · ${missingDates.length} blank readings shown as gaps${missingDates.length ? ` (${missingDates.join(", ")})` : ""}.`,
  );
  renderYearTable(data.historical.yearly_summary || []);
  renderQuality(data.quality);
  renderForecast(data.forecast);
  text("source-name", data.source.name || "PAQI Karachi daily PM2.5 dataset");
  text("source-publisher", data.source.publisher);
  setSafeLink(document.getElementById("source-link"), data.source.url, "Open pinned dataset record ↗");
  setSafeLink(document.getElementById("license-link"), data.source.license_url, "CC BY 4.0 licence ↗");
  text("source-license", data.source.license_summary);
  text("attribution", data.source.attribution);
  text("page-generated", `Dashboard data assembled ${data.generated_at_utc}`);
  document.getElementById("dashboard-content").hidden = false;
  document.getElementById("loading").hidden = true;
}

function renderInsight(result) {
  const panel = document.getElementById("answer-panel");
  panel.replaceChildren();
  const status = element("span", `answer-status ${result.status}`);
  status.textContent = result.status.replaceAll("_", " ");
  panel.append(status);
  panel.append(element("h3", "", "Evidence-grounded answer"));
  panel.append(element("p", "answer-copy", result.answer));
  panel.append(element("p", "answer-meta", `Data as of ${result.data_as_of} · Generated ${result.generated_at}`));
  if (result.evidence && result.evidence.length) {
    panel.append(element("h3", "", "Evidence references"));
    const list = element("ul", "evidence-list");
    result.evidence.forEach((item) => {
      const entry = element("li", "");
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

document.getElementById("question-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.getElementById("ask-button");
  const panel = document.getElementById("answer-panel");
  const question = document.getElementById("question").value.trim();
  if (!question) return;
  button.disabled = true;
  button.textContent = "Retrieving evidence…";
  panel.setAttribute("aria-busy", "true");
  panel.replaceChildren(element("p", "muted", "The local Insight Agent is checking the project evidence…"));
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ question }),
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
});

loadDashboard();
