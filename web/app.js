const form = document.querySelector("#searchForm");
const batchForm = document.querySelector("#batchForm");
const navButtons = document.querySelectorAll(".navButton");
const globalMarket = document.querySelector("#globalMarket");
const symbolInput = document.querySelector("#symbolInput");
const periodInput = document.querySelector("#periodInput");
const batchSearch = document.querySelector("#batchSearch");
const prevHistory = document.querySelector("#prevHistory");
const nextHistory = document.querySelector("#nextHistory");
const statusEl = document.querySelector("#status");
const canvas = document.querySelector("#priceChart");
const ctx = canvas.getContext("2d");
const lrcCanvas = document.querySelector("#lrcChart");
const lrcCtx = lrcCanvas.getContext("2d");

const fields = {
  latestClose: document.querySelector("#latestClose"),
  latestDate: document.querySelector("#latestDate"),
  periodReturn: document.querySelector("#periodReturn"),
  drawdown: document.querySelector("#drawdown"),
  range52w: document.querySelector("#range52w"),
  score: document.querySelector("#score"),
  scoreLabel: document.querySelector("#scoreLabel"),
  chartTitle: document.querySelector("#chartTitle"),
  rowCount: document.querySelector("#rowCount"),
  signals: document.querySelector("#signals"),
  historyBody: document.querySelector("#historyBody"),
  batchStatus: document.querySelector("#batchStatus"),
  batchBody: document.querySelector("#batchBody"),
  batchSource: document.querySelector("#batchSource"),
  batchGenerated: document.querySelector("#batchGenerated"),
  batchCount: document.querySelector("#batchCount"),
  batchWindow: document.querySelector("#batchWindow"),
  historyPage: document.querySelector("#historyPage"),
};

const HISTORY_PAGE_SIZE = 30;
let historyPageIndex = 0;
let historyRows = [];
let batchPayload = null;

navButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showView(button.dataset.view);
  });
});

globalMarket.addEventListener("change", () => {
  if (document.querySelector("#batchView").classList.contains("active")) {
    loadBatch();
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadAnalysis();
});

batchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadBatch();
});

batchSearch.addEventListener("input", () => {
  if (batchPayload) renderBatch(batchPayload);
});

prevHistory.addEventListener("click", () => {
  if (historyPageIndex > 0) {
    historyPageIndex -= 1;
    renderHistoryPage();
  }
});

nextHistory.addEventListener("click", () => {
  if ((historyPageIndex + 1) * HISTORY_PAGE_SIZE < historyRows.length) {
    historyPageIndex += 1;
    renderHistoryPage();
  }
});

window.addEventListener("resize", () => {
  if (window.currentRows) drawChart(window.currentRows);
});

loadAnalysis();
showView(location.hash === "#batch" ? "batchView" : "singleView");

function showView(viewId) {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === viewId);
  });
  navButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewId);
  });
  history.replaceState(null, "", viewId === "batchView" ? "#batch" : "#single");
  if (viewId === "batchView" && !window.batchLoaded) {
    loadBatch();
  }
  if (viewId === "singleView" && window.currentRows) {
    requestAnimationFrame(() => {
      drawChart(window.currentRows);
      if (window.currentLrc) drawLrcChart(window.currentLrc);
    });
  }
}

async function loadAnalysis() {
  const symbol = symbolInput.value.trim() || "AAPL";
  const period = periodInput.value;
  setLoading(true, `正在读取 ${symbol.toUpperCase()} ...`);
  try {
    const response = await fetch(`/api/analyze?symbol=${encodeURIComponent(symbol)}&period=${period}`);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || "请求失败");
    render(payload);
    statusEl.textContent = `${payload.symbol} 分析完成。数据会本地缓存约15分钟。`;
    statusEl.classList.remove("error");
  } catch (error) {
    statusEl.textContent = error.message;
    statusEl.classList.add("error");
  } finally {
    setLoading(false);
  }
}

async function loadBatch() {
  const params = new URLSearchParams({
    markets: globalMarket.value,
  });
  const button = batchForm.querySelector("button");
  button.disabled = true;
  fields.batchStatus.textContent = "正在读取预计算 Sigma Model ...";
  fields.batchStatus.classList.remove("error");
  try {
    const response = await fetch(`/api/batch?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || "批量请求失败");
    batchPayload = payload;
    renderBatch(payload);
    window.batchLoaded = true;
    const filters = [
      payload.markets.length ? `markets=${payload.markets.join(",")}` : "",
    ].filter(Boolean).join("; ");
    fields.batchStatus.textContent = `${payload.symbolsFile} / ${payload.source || "precomputed"}${filters ? ` / ${filters}` : ""}`;
  } catch (error) {
    fields.batchStatus.textContent = error.message;
    fields.batchStatus.classList.add("error");
  } finally {
    button.disabled = false;
  }
}

function render(payload) {
  const latest = payload.latest;
  window.currentRows = payload.rows;
  window.currentLrc = payload.lrc || [];
  fields.latestClose.textContent = money(latest.close);
  fields.latestDate.textContent = latest.date;
  fields.periodReturn.textContent = pct(payload.periodReturnPct);
  fields.periodReturn.className = payload.periodReturnPct >= 0 ? "up" : "down";
  fields.drawdown.textContent = pct(payload.drawdownPct);
  fields.range52w.textContent = `${money(payload.low52w)} - ${money(payload.high52w)}`;
  fields.score.textContent = payload.score.value;
  fields.scoreLabel.textContent = payload.score.label;
  fields.chartTitle.textContent = `${payload.symbol} 价格走势`;
  fields.rowCount.textContent = `${payload.rows.length} 条`;
  renderSignals(payload.signals);
  historyRows = [...payload.rows].reverse();
  historyPageIndex = 0;
  renderHistoryPage();
  drawChart(payload.rows);
  drawLrcChart(payload.lrc || []);
}

function renderSignals(signals) {
  fields.signals.innerHTML = "";
  for (const signal of signals) {
    const node = document.createElement("article");
    node.className = `signal ${signal.sentiment}`;
    node.innerHTML = `
      <div class="signalHeader">
        <strong>${escapeHtml(signal.label)}</strong>
        <span>${escapeHtml(signal.value)}</span>
      </div>
      <small>${escapeHtml(signal.detail)}</small>
    `;
    fields.signals.appendChild(node);
  }
}

function renderHistoryPage() {
  const pageCount = Math.max(1, Math.ceil(historyRows.length / HISTORY_PAGE_SIZE));
  const start = historyPageIndex * HISTORY_PAGE_SIZE;
  renderTable(historyRows.slice(start, start + HISTORY_PAGE_SIZE));
  fields.rowCount.textContent = `${historyRows.length} 条`;
  fields.historyPage.textContent = `${historyPageIndex + 1} / ${pageCount}`;
  prevHistory.disabled = historyPageIndex === 0;
  nextHistory.disabled = historyPageIndex >= pageCount - 1;
}

function renderTable(rows) {
  fields.historyBody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.date}</td>
      <td>${money(row.open)}</td>
      <td>${money(row.high)}</td>
      <td>${money(row.low)}</td>
      <td>${money(row.close)}</td>
      <td class="${row.change_pct >= 0 ? "up" : "down"}">${pct(row.change_pct)}</td>
      <td>${row.rsi14 == null ? "-" : row.rsi14.toFixed(1)}</td>
      <td>${compact(row.volume)}</td>
    `;
    fields.historyBody.appendChild(tr);
  }
}

function renderBatch(payload) {
  fields.batchBody.innerHTML = "";
  fields.batchSource.textContent = payload.source === "live" ? "实时计算" : "预计算";
  fields.batchGenerated.textContent = payload.generatedAt ? formatDateTime(payload.generatedAt) : "-";
  const filteredRows = filterBatchRows(payload.results || []);
  fields.batchCount.textContent = filteredRows.length;
  fields.batchWindow.textContent = payload.window ? `${payload.window}日` : "200日";
  if (!filteredRows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="9" class="emptyCell">没有匹配结果。请确认 symbols.xlsx 的市场筛选，或运行 sh update_cache.sh 重新生成预计算结果。</td>`;
    fields.batchBody.appendChild(tr);
    return;
  }
  for (const row of filteredRows) {
    const tr = document.createElement("tr");
    if (row.ok) {
      const rowFields = row.fields || {};
      tr.className = "clickableRow";
      tr.title = "打开单股分析";
      tr.addEventListener("click", () => openSingleStock(row.symbol));
      tr.innerHTML = `
        <td>${escapeHtml(valueOrDash(rowFields["代碼"] || row.symbol))}</td>
        <td class="${row.zScore >= 0 ? "up" : "down"}">${numberOrDash(rowFields["LRC Z-score"], 2)}</td>
        <td>${escapeHtml(valueOrDash(rowFields["名稱"]))}</td>
        <td>${numberOrDash(rowFields["最新價"], 2)}</td>
        <td class="${Number(rowFields["漲跌幅"]) >= 0 ? "up" : "down"}">${percentOrDash(rowFields["漲跌幅"])}</td>
        <td>${compactOrDash(rowFields["成交量"])}</td>
        <td>${numberOrDash(rowFields["MA-MA200-日線"], 2)}</td>
        <td>${numberOrDash(rowFields["RSI-RSI14-日線"], 1)}</td>
        <td>${escapeHtml(valueOrDash(rowFields["所屬行業"]))}</td>
      `;
    } else {
      tr.innerHTML = `
        <td>${escapeHtml(row.symbol)}</td>
        <td colspan="7">-</td>
        <td class="error">${escapeHtml(row.error)}</td>
      `;
    }
    fields.batchBody.appendChild(tr);
  }
}

function filterBatchRows(rows) {
  const query = batchSearch.value.trim().toUpperCase();
  if (!query) return rows;
  return rows.filter((row) => {
    const rowFields = row.fields || {};
    return [
      row.symbol,
      rowFields["代碼"],
      rowFields["名稱"],
      rowFields["所屬行業"],
    ].some((value) => String(value || "").toUpperCase().includes(query));
  });
}

function openSingleStock(symbol) {
  symbolInput.value = symbol;
  showView("singleView");
  loadAnalysis();
}

function drawChart(rows) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.floor(rect.width * ratio);
  canvas.height = Math.floor(rect.height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

  const width = rect.width;
  const height = rect.height;
  const pad = { top: 24, right: 58, bottom: 34, left: 48 };
  ctx.clearRect(0, 0, width, height);

  const series = rows.map((row) => row.close);
  const overlays = [
    rows.map((row) => row.sma20),
    rows.map((row) => row.sma50),
  ];
  const values = [...series, ...overlays.flat().filter((value) => value != null)];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const x = (idx) => pad.left + (idx / Math.max(rows.length - 1, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((max - value) / span) * (height - pad.top - pad.bottom);

  drawGrid(width, height, pad, min, max, y);
  drawLine(series, x, y, "#17202a", 2.4);
  drawLine(overlays[0], x, y, "#0f766e", 1.8);
  drawLine(overlays[1], x, y, "#2563eb", 1.8);
  drawLegend(width, pad);
}

function drawLrcChart(rows) {
  const ratio = window.devicePixelRatio || 1;
  const rect = lrcCanvas.getBoundingClientRect();
  lrcCanvas.width = Math.floor(rect.width * ratio);
  lrcCanvas.height = Math.floor(rect.height * ratio);
  lrcCtx.setTransform(ratio, 0, 0, ratio, 0, 0);

  const width = rect.width;
  const height = rect.height;
  const pad = { top: 24, right: 58, bottom: 34, left: 48 };
  lrcCtx.clearRect(0, 0, width, height);
  if (!rows.length) {
    lrcCtx.fillStyle = "#5e6b78";
    lrcCtx.font = "13px Segoe UI, Arial";
    lrcCtx.fillText("LRC 数据不足", pad.left, pad.top + 16);
    return;
  }

  const keys = ["close", "trend", "upper2", "lower2", "upper4", "lower4"];
  const values = rows.flatMap((row) => keys.map((key) => row[key]).filter((value) => value != null));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const x = (idx) => pad.left + (idx / Math.max(rows.length - 1, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((max - value) / span) * (height - pad.top - pad.bottom);

  drawLrcGrid(width, height, pad, min, max, y);
  drawBand(rows.map((row) => row.upper4), rows.map((row) => row.lower4), x, y, "rgba(37, 99, 235, 0.08)");
  drawBand(rows.map((row) => row.upper2), rows.map((row) => row.lower2), x, y, "rgba(15, 118, 110, 0.12)");
  drawLrcLine(rows.map((row) => row.upper4), x, y, "#94a3b8", 1);
  drawLrcLine(rows.map((row) => row.lower4), x, y, "#94a3b8", 1);
  drawLrcLine(rows.map((row) => row.upper2), x, y, "#0f766e", 1.4);
  drawLrcLine(rows.map((row) => row.lower2), x, y, "#0f766e", 1.4);
  drawLrcLine(rows.map((row) => row.trend), x, y, "#2563eb", 2);
  drawLrcLine(rows.map((row) => row.close), x, y, "#17202a", 2.2);
  drawLrcLegend(pad);
}

function drawLrcGrid(width, height, pad, min, max, y) {
  lrcCtx.strokeStyle = "#e5eaf0";
  lrcCtx.fillStyle = "#5e6b78";
  lrcCtx.lineWidth = 1;
  lrcCtx.font = "12px Segoe UI, Arial";
  for (let i = 0; i <= 4; i += 1) {
    const value = min + ((max - min) * i) / 4;
    const lineY = y(value);
    lrcCtx.beginPath();
    lrcCtx.moveTo(pad.left, lineY);
    lrcCtx.lineTo(width - pad.right, lineY);
    lrcCtx.stroke();
    lrcCtx.fillText(value.toFixed(2), width - pad.right + 8, lineY + 4);
  }
  lrcCtx.strokeStyle = "#cbd5df";
  lrcCtx.strokeRect(pad.left, pad.top, width - pad.left - pad.right, height - pad.top - pad.bottom);
}

function drawBand(upper, lower, x, y, color) {
  lrcCtx.beginPath();
  upper.forEach((value, idx) => {
    if (idx === 0) lrcCtx.moveTo(x(idx), y(value));
    else lrcCtx.lineTo(x(idx), y(value));
  });
  [...lower].reverse().forEach((value, reverseIdx) => {
    const idx = lower.length - 1 - reverseIdx;
    lrcCtx.lineTo(x(idx), y(value));
  });
  lrcCtx.closePath();
  lrcCtx.fillStyle = color;
  lrcCtx.fill();
}

function drawLrcLine(values, x, y, color, lineWidth) {
  lrcCtx.beginPath();
  lrcCtx.strokeStyle = color;
  lrcCtx.lineWidth = lineWidth;
  values.forEach((value, idx) => {
    if (idx === 0) lrcCtx.moveTo(x(idx), y(value));
    else lrcCtx.lineTo(x(idx), y(value));
  });
  lrcCtx.stroke();
}

function drawLrcLegend(pad) {
  const items = [
    ["Close", "#17202a"],
    ["Trend", "#2563eb"],
    ["±2σ", "#0f766e"],
    ["±4σ", "#94a3b8"],
  ];
  let offset = pad.left;
  lrcCtx.font = "12px Segoe UI, Arial";
  for (const [label, color] of items) {
    lrcCtx.fillStyle = color;
    lrcCtx.fillRect(offset, 10, 18, 3);
    lrcCtx.fillStyle = "#5e6b78";
    lrcCtx.fillText(label, offset + 24, 14);
    offset += 86;
  }
}

function drawGrid(width, height, pad, min, max, y) {
  ctx.strokeStyle = "#e5eaf0";
  ctx.fillStyle = "#5e6b78";
  ctx.lineWidth = 1;
  ctx.font = "12px Segoe UI, Arial";
  for (let i = 0; i <= 4; i += 1) {
    const value = min + ((max - min) * i) / 4;
    const lineY = y(value);
    ctx.beginPath();
    ctx.moveTo(pad.left, lineY);
    ctx.lineTo(width - pad.right, lineY);
    ctx.stroke();
    ctx.fillText(value.toFixed(2), width - pad.right + 8, lineY + 4);
  }
  ctx.strokeStyle = "#cbd5df";
  ctx.strokeRect(pad.left, pad.top, width - pad.left - pad.right, height - pad.top - pad.bottom);
}

function drawLine(values, x, y, color, lineWidth) {
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  let started = false;
  values.forEach((value, idx) => {
    if (value == null) return;
    if (!started) {
      ctx.moveTo(x(idx), y(value));
      started = true;
    } else {
      ctx.lineTo(x(idx), y(value));
    }
  });
  ctx.stroke();
}

function drawLegend(width, pad) {
  const items = [
    ["Close", "#17202a"],
    ["SMA20", "#0f766e"],
    ["SMA50", "#2563eb"],
  ];
  let offset = pad.left;
  ctx.font = "12px Segoe UI, Arial";
  for (const [label, color] of items) {
    ctx.fillStyle = color;
    ctx.fillRect(offset, 10, 18, 3);
    ctx.fillStyle = "#5e6b78";
    ctx.fillText(label, offset + 24, 14);
    offset += 88;
  }
}

function setLoading(loading, message) {
  form.querySelector("button").disabled = loading;
  if (message) statusEl.textContent = message;
}

function money(value) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function pct(value) {
  const number = Number(value);
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
}

function compact(value) {
  return Number(value).toLocaleString(undefined, { notation: "compact", maximumFractionDigits: 2 });
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

function numberOrDash(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function percentOrDash(value) {
  if (value === null || value === undefined || value === "") return "-";
  return pct(value);
}

function compactOrDash(value) {
  if (value === null || value === undefined || value === "") return "-";
  return compact(value);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function batchLabel(zScore) {
  if (zScore <= -2) return "低于 -2σ";
  if (zScore <= -1) return "偏低";
  if (zScore >= 2) return "高于 +2σ";
  if (zScore >= 1) return "偏高";
  return "中性";
}

function formatDateTime(value) {
  return new Date(value).toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
