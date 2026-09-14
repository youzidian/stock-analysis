const form = document.querySelector("#searchForm");
const batchForm = document.querySelector("#batchForm");
const maSlopeForm = document.querySelector("#maSlopeForm");
const navButtons = document.querySelectorAll(".navButton");
const globalMarket = document.querySelector("#globalMarket");
const languageInput = document.querySelector("#languageInput");
const symbolInput = document.querySelector("#symbolInput");
const periodInput = document.querySelector("#periodInput");
const batchSearch = document.querySelector("#batchSearch");
const batchIndustryFilter = document.querySelector("#batchIndustryFilter");
const batchPriceMaRelations = [
  document.querySelector("#batchPriceMa20Relation"),
  document.querySelector("#batchPriceMa50Relation"),
  document.querySelector("#batchPriceMa200Relation"),
  document.querySelector("#batchMa50Ma200Relation"),
];
const batchFilterInputs = [
  document.querySelector("#batchZMin"),
  document.querySelector("#batchZMax"),
  document.querySelector("#batchRsiMin"),
  document.querySelector("#batchRsiMax"),
  document.querySelector("#batchMarketCapMin"),
  document.querySelector("#batchMarketCapMax"),
  document.querySelector("#batchOperatingProfitMin"),
  document.querySelector("#batchOperatingProfitMax"),
];
const batchShowErrors = document.querySelector("#batchShowErrors");
const batchClearFilters = document.querySelector("#batchClearFilters");
const batchPageSize = document.querySelector("#batchPageSize");
const prevBatchPage = document.querySelector("#prevBatchPage");
const nextBatchPage = document.querySelector("#nextBatchPage");
const sortButtons = document.querySelectorAll(".sortButton");
const prevHistory = document.querySelector("#prevHistory");
const nextHistory = document.querySelector("#nextHistory");
const statusEl = document.querySelector("#status");
const canvas = document.querySelector("#priceChart");
const ctx = canvas.getContext("2d");
const lrcCanvas = document.querySelector("#lrcChart");
const lrcCtx = lrcCanvas.getContext("2d");
const priceTooltip = document.querySelector("#priceTooltip");
const lrcTooltip = document.querySelector("#lrcTooltip");
const maSlopePriceCanvas = document.querySelector("#maSlopePriceChart");
const maSlopePriceCtx = maSlopePriceCanvas.getContext("2d");
const maSlopeCanvas = document.querySelector("#maSlopeChart");
const maSlopeCtx = maSlopeCanvas.getContext("2d");
const maSlopePriceTooltip = document.querySelector("#maSlopePriceTooltip");
const maSlopeTooltip = document.querySelector("#maSlopeTooltip");
const maSlopeSymbol = document.querySelector("#maSlopeSymbol");
const maSlopePeriod = document.querySelector("#maSlopePeriod");
const maSlopePeriods = document.querySelector("#maSlopePeriods");
const maSlopeWindow = document.querySelector("#maSlopeWindow");
const maSlopeWindowValue = document.querySelector("#maSlopeWindowValue");
const maSlopeVolume = document.querySelector("#maSlopeVolume");
const maSlopeLogScale = document.querySelector("#maSlopeLogScale");

const fields = {
  analysisTitle: document.querySelector("#analysisTitle"),
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
  batchRowCount: document.querySelector("#batchRowCount"),
  batchPage: document.querySelector("#batchPage"),
  historyPage: document.querySelector("#historyPage"),
  maSlopeTitle: document.querySelector("#maSlopeTitle"),
  maSlopeStatus: document.querySelector("#maSlopeStatus"),
  maSlopeMetrics: document.querySelector("#maSlopeMetrics"),
  maSlopePriceHint: document.querySelector("#maSlopePriceHint"),
  maSlopeChartTitle: document.querySelector("#maSlopeChartTitle"),
  maSlopeRange: document.querySelector("#maSlopeRange"),
  maSlopeStatsBody: document.querySelector("#maSlopeStatsBody"),
  maSlopeRawHead: document.querySelector("#maSlopeRawHead"),
  maSlopeRawBody: document.querySelector("#maSlopeRawBody"),
  maSlopePriceLegend: document.querySelector("#maSlopePriceLegend"),
  maSlopeLegend: document.querySelector("#maSlopeLegend"),
};

const HISTORY_PAGE_SIZE = 30;
let historyPageIndex = 0;
let historyRows = [];
let batchPayload = null;
let batchPageIndex = 0;
let batchSort = { key: "zScore", direction: "asc" };
let maSlopePayload = null;
let currentAnalysisPayload = null;
let currentLanguage = localStorage.getItem("stockAnalysisLanguage") || "en";
const maSlopePriceHidden = new Set();
const maSlopeHidden = new Set();

const translations = {
  en: {
    appTitle: "Local Stock Analysis",
    navSigma: "Sigma Model",
    navSingle: "Single Stock",
    navMaSlope: "MA Slope",
    language: "Language",
    globalMarket: "Global Market",
    all: "All",
    statusIntro: "Enter a symbol to load daily data and generate a technical summary.",
    symbol: "Symbol",
    period: "Period",
    analyze: "Analyze",
    latestClose: "Latest Close",
    periodReturn: "Period Return",
    periodReturnHint: "Based on the selected period",
    drawdown52w: "52W Drawdown",
    compositeScore: "Composite Score",
    priceTrend: "Price Trend",
    signals: "Signals",
    researchOnly: "Research only",
    recentTradingDays: "Recent Trading Days",
    date: "Date",
    open: "Open",
    high: "High",
    low: "Low",
    close: "Close",
    changePct: "Change %",
    volume: "Volume",
    search: "Search",
    searchPlaceholder: "Symbol / name / industry",
    run: "Run",
    batchIntro: "Load the daily precomputed LRC Z-score snapshot",
    source: "Source",
    generatedAt: "Generated At",
    resultCount: "Result Count",
    lrcWindow: "LRC Window",
    industry: "Industry",
    allIndustries: "All Industries",
    min: "Min",
    max: "Max",
    to: "to",
    marketCap: "Market Cap",
    priceMa20: "Price / MA20",
    priceMa50: "Price / MA50",
    priceMa200: "Price / MA200",
    anyRelation: "Any relation",
    priceAbove: "Price above {ma}",
    priceBelow: "Price below {ma}",
    priceNear: "Price near {ma}",
    ma50Above: "MA50 above MA200",
    ma50Below: "MA50 below MA200",
    ma50Near: "MA50 near MA200",
    operatingProfitTtm: "Operating Profit TTM",
    showFailedRows: "Show failed rows",
    clear: "Clear",
    screeningResults: "Screening Results",
    perPage: "Per page",
    name: "Name",
    latest: "Latest",
    displayPeriod: "Display Period",
    maPeriods: "MA Periods",
    slopeLookback: "Slope lookback (trading days)",
    showVolume: "Show volume",
    logPrice: "Log price",
    maSlopeIntro: "Calculate moving averages and daily slopes from the local ten-year cache.",
    maSlopeMetrics: "MA Slope metrics",
    priceAndMa: "Price and Moving Averages",
    percentPerDay: "% / trading day",
    slopeStatistics: "Slope Statistics",
    current: "Current",
    mean: "Mean",
    stdDev: "Std Dev",
    minDate: "Min Date",
    negativeDaysPct: "Negative Days %",
    rawData: "Raw Data: Last 30 Rows",
    loadingSymbol: "Loading {symbol} ...",
    requestFailed: "Request failed",
    analysisReady: "{symbol} analysis is ready. Data is cached locally for about 15 minutes.",
    loadingBatch: "Loading precomputed Sigma Model ...",
    batchRequestFailed: "Batch request failed",
    calculatingSlope: "Calculating {symbol} from the local cache ...",
    maSlopeRequestFailed: "MA Slope request failed",
    tradingDays: "{date}, {count} trading days.",
    rows: "{count} rows",
    days: "{count} days",
    noMatches: "No matching results. Check the market filter in symbols.xlsx or run sh update_cache.sh to regenerate the precomputed snapshot.",
    openSingle: "Open single stock analysis",
    live: "Live",
    precomputed: "Precomputed",
    notEnoughLrc: "Not enough LRC data",
    selectPriceLine: "Select at least one price line",
    selectSlopeLine: "Select at least one slope line",
    vsLatestPrice: "vs latest price",
    slope: "Slope",
    percentile: "percentile",
    slopeTitle: "MA Slope ({days}-day lookback)",
    dateRange: "{start} to {end}",
    belowMinus2: "Below -2σ",
    lowLabel: "Low",
    abovePlus2: "Above +2σ",
    highLabel: "High",
    neutral: "Neutral",
    shortMidTrend: "Short/Mid-Term Trend",
    bullishAlignment: "Bullish alignment",
    notConfirmed: "Not confirmed",
    longTermPosition: "Long-Term Position",
    above200: "Above 200-day MA",
    below200: "Below 200-day MA",
    hot: "Hot",
    cold: "Cold",
    elevated: "Elevated",
    normal: "Normal",
    nearHigh: "Near high",
    nearLow: "Near low",
    midRange: "Mid range",
    strongWatch: "Strong watch",
    moderatelyStrong: "Moderately strong",
    weak: "Weak",
    currentRsi: "Current RSI {value}",
    volumeDetail: "Latest volume is {value}x the 20-day average",
    maDetail: "Close {close}, 20-day MA {ma20}, 50-day MA {ma50}",
    ma200Detail: "200-day MA {value}",
    drawdownDetail: "{value}% from the 52-week high",
  },
  "zh-Hant": {
    appTitle: "本地股市分析",
    navSigma: "Sigma Model",
    navSingle: "單股分析",
    navMaSlope: "MA Slope",
    language: "語言",
    globalMarket: "全域市場",
    all: "全部",
    statusIntro: "輸入股票代碼後讀取日線資料並生成技術摘要。",
    symbol: "股票代碼",
    period: "週期",
    analyze: "分析",
    latestClose: "最新收盤",
    periodReturn: "區間收益",
    periodReturnHint: "按所選週期計算",
    drawdown52w: "52週回撤",
    compositeScore: "綜合評分",
    priceTrend: "價格走勢",
    signals: "訊號",
    researchOnly: "僅供研究",
    recentTradingDays: "最近交易日",
    date: "日期",
    open: "開盤",
    high: "最高",
    low: "最低",
    close: "收盤",
    changePct: "漲跌幅",
    volume: "成交量",
    search: "搜尋",
    searchPlaceholder: "代碼 / 名稱 / 行業",
    run: "執行",
    batchIntro: "讀取每日預先計算的 LRC Z-score",
    source: "來源",
    generatedAt: "生成時間",
    resultCount: "結果數量",
    lrcWindow: "LRC 視窗",
    industry: "行業",
    allIndustries: "全部行業",
    min: "最小",
    max: "最大",
    to: "至",
    marketCap: "市值",
    priceMa20: "最新價 / MA20",
    priceMa50: "最新價 / MA50",
    priceMa200: "最新價 / MA200",
    anyRelation: "全部關係",
    priceAbove: "最新價高於 {ma}",
    priceBelow: "最新價低於 {ma}",
    priceNear: "最新價接近 {ma}",
    ma50Above: "MA50 高於 MA200",
    ma50Below: "MA50 低於 MA200",
    ma50Near: "MA50 接近 MA200",
    operatingProfitTtm: "營業利潤 TTM",
    showFailedRows: "顯示失敗項",
    clear: "清除",
    screeningResults: "篩選結果",
    perPage: "每頁",
    name: "名稱",
    latest: "最新價",
    displayPeriod: "顯示週期",
    maPeriods: "MA 週期",
    slopeLookback: "Slope lookback（交易日）",
    showVolume: "顯示成交量",
    logPrice: "對數價格",
    maSlopeIntro: "從本地十年快取計算移動均線及每日斜率。",
    maSlopeMetrics: "MA Slope 指標",
    priceAndMa: "價格與移動均線",
    percentPerDay: "% / 交易日",
    slopeStatistics: "Slope 統計",
    current: "目前",
    mean: "均值",
    stdDev: "標準差",
    minDate: "最小值日期",
    negativeDaysPct: "負斜率占比",
    rawData: "最近 30 行原始資料",
    loadingSymbol: "正在讀取 {symbol} ...",
    requestFailed: "請求失敗",
    analysisReady: "{symbol} 分析完成。資料會在本地快取約 15 分鐘。",
    loadingBatch: "正在讀取預先計算的 Sigma Model ...",
    batchRequestFailed: "批量請求失敗",
    calculatingSlope: "正在從本地快取計算 {symbol} ...",
    maSlopeRequestFailed: "MA Slope 請求失敗",
    tradingDays: "{date}，共 {count} 個交易日。",
    rows: "{count} 筆",
    days: "{count} 日",
    noMatches: "沒有符合條件的結果。請確認 symbols.xlsx 的市場篩選，或執行 sh update_cache.sh 重新生成預計算結果。",
    openSingle: "開啟單股分析",
    live: "即時計算",
    precomputed: "預先計算",
    notEnoughLrc: "LRC 資料不足",
    selectPriceLine: "請至少選擇一條價格線",
    selectSlopeLine: "請至少選擇一條斜率線",
    vsLatestPrice: "vs 最新價",
    slope: "斜率",
    percentile: "百分位",
    slopeTitle: "均線斜率（{days} 日 lookback）",
    dateRange: "{start} 至 {end}",
    belowMinus2: "低於 -2σ",
    lowLabel: "偏低",
    abovePlus2: "高於 +2σ",
    highLabel: "偏高",
    neutral: "中性",
    shortMidTrend: "短中期趨勢",
    bullishAlignment: "多頭排列",
    notConfirmed: "未確認",
    longTermPosition: "長期位置",
    above200: "站上 200 日線",
    below200: "低於 200 日線",
    hot: "偏熱",
    cold: "偏冷",
    elevated: "明顯放量",
    normal: "常規",
    nearHigh: "接近高位",
    nearLow: "接近低位",
    midRange: "區間中部",
    strongWatch: "強勢觀察",
    moderatelyStrong: "偏強",
    weak: "偏弱",
    currentRsi: "目前 RSI {value}",
    volumeDetail: "最新成交量是 20 日均量的 {value} 倍",
    maDetail: "收盤價 {close}，20 日均線 {ma20}，50 日均線 {ma50}",
    ma200Detail: "200 日均線 {value}",
    drawdownDetail: "距 52 週高點 {value}%",
  },
};

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

languageInput.value = translations[currentLanguage] ? currentLanguage : "en";
currentLanguage = languageInput.value;
languageInput.addEventListener("change", () => {
  currentLanguage = languageInput.value;
  localStorage.setItem("stockAnalysisLanguage", currentLanguage);
  applyLanguage();
  rerenderCurrentData();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadAnalysis();
});

batchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadBatch();
});

maSlopeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadMaSlope();
});

maSlopeWindow.addEventListener("input", () => {
  maSlopeWindowValue.value = maSlopeWindow.value;
});

maSlopeWindow.addEventListener("change", () => {
  loadMaSlope();
});

[maSlopeVolume, maSlopeLogScale].forEach((input) => {
  input.addEventListener("change", () => {
    if (maSlopePayload) {
      drawMaSlopePriceChart(maSlopePayload.rows);
    }
  });
});

batchSearch.addEventListener("input", () => {
  batchPageIndex = 0;
  if (batchPayload) renderBatch(batchPayload);
});

batchIndustryFilter.addEventListener("change", () => {
  batchPageIndex = 0;
  if (batchPayload) renderBatch(batchPayload);
});

batchPriceMaRelations.forEach((select) => {
  select.addEventListener("change", () => {
    batchPageIndex = 0;
    if (batchPayload) renderBatch(batchPayload);
  });
});

batchFilterInputs.forEach((input) => {
  input.addEventListener("input", () => {
    batchPageIndex = 0;
    if (batchPayload) renderBatch(batchPayload);
  });
});

batchShowErrors.addEventListener("change", () => {
  batchPageIndex = 0;
  if (batchPayload) renderBatch(batchPayload);
});

batchClearFilters.addEventListener("click", () => {
  batchSearch.value = "";
  batchIndustryFilter.value = "";
  batchPriceMaRelations.forEach((select) => {
    select.value = "";
  });
  batchFilterInputs.forEach((input) => {
    input.value = "";
  });
  batchShowErrors.checked = false;
  batchPageIndex = 0;
  if (batchPayload) renderBatch(batchPayload);
});

batchPageSize.addEventListener("change", () => {
  batchPageIndex = 0;
  if (batchPayload) renderBatch(batchPayload);
});

prevBatchPage.addEventListener("click", () => {
  if (batchPageIndex > 0) {
    batchPageIndex -= 1;
    if (batchPayload) renderBatch(batchPayload);
  }
});

nextBatchPage.addEventListener("click", () => {
  if (!batchPayload) return;
  const pageSize = Number(batchPageSize.value);
  const totalRows = sortBatchRows(filterBatchRows(batchPayload.results || [])).length;
  if ((batchPageIndex + 1) * pageSize < totalRows) {
    batchPageIndex += 1;
    renderBatch(batchPayload);
  }
});

sortButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.sort;
    batchSort = {
      key,
      direction: batchSort.key === key && batchSort.direction === "asc" ? "desc" : "asc",
    };
    batchPageIndex = 0;
    if (batchPayload) renderBatch(batchPayload);
  });
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
  if (window.currentRows) {
    drawChart(window.currentRows);
    if (window.currentLrc) drawLrcChart(window.currentLrc);
  }
  if (maSlopePayload) {
    drawMaSlopePriceChart(maSlopePayload.rows);
    drawMaSlopeChart(maSlopePayload.rows);
  }
});

bindChartTooltip(canvas, priceTooltip, () => window.currentRows || [], drawChart, priceTooltipHtml);
bindChartTooltip(lrcCanvas, lrcTooltip, () => window.currentLrc || [], drawLrcChart, lrcTooltipHtml);
bindChartTooltip(
  maSlopePriceCanvas,
  maSlopePriceTooltip,
  () => maSlopePayload?.rows || [],
  drawMaSlopePriceChart,
  maSlopePriceTooltipHtml,
);
bindChartTooltip(
  maSlopeCanvas,
  maSlopeTooltip,
  () => maSlopePayload?.rows || [],
  drawMaSlopeChart,
  maSlopeTooltipHtml,
);

applyLanguage();
showView({
  "#single": "singleView",
  "#batch": "batchView",
  "#ma-slope": "maSlopeView",
}[location.hash] || "batchView");

function t(key, values = {}) {
  const template = translations[currentLanguage]?.[key] ?? translations.en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");
}

function setText(selector, text) {
  const element = document.querySelector(selector);
  if (element) element.textContent = text;
}

function setAllText(selector, values) {
  document.querySelectorAll(selector).forEach((element, index) => {
    if (values[index] !== undefined) element.textContent = values[index];
  });
}

function setPlaceholder(selector, text) {
  const element = document.querySelector(selector);
  if (element) element.placeholder = text;
}

function setClosestLabelText(selector, text) {
  const element = document.querySelector(selector);
  const label = element?.closest("label");
  const span = label?.querySelector("span");
  if (span) span.textContent = text;
}

function setClosestLegend(selector, text) {
  const element = document.querySelector(selector);
  const legend = element?.closest("fieldset")?.querySelector("legend");
  if (legend) legend.textContent = text;
}

function setOptionText(selector, value, text) {
  const option = document.querySelector(`${selector} option[value="${value}"]`);
  if (option) option.textContent = text;
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage;
  document.title = t("appTitle");
  setText('.navButton[data-view="batchView"]', t("navSigma"));
  setText('.navButton[data-view="singleView"]', t("navSingle"));
  setText('.navButton[data-view="maSlopeView"]', t("navMaSlope"));
  setText(".languageControl span", t("language"));
  setText(".globalMarket span", t("globalMarket"));
  setOptionText("#globalMarket", "", t("all"));

  if (!currentAnalysisPayload) {
    fields.analysisTitle.textContent = t("appTitle");
    statusEl.textContent = t("statusIntro");
  }
  setAllText("#searchForm label span", [t("symbol"), t("period")]);
  setText("#searchForm button", t("analyze"));
  setPeriodOptions("#periodInput");
  setAllText(".metrics article > span", [
    t("latestClose"),
    t("periodReturn"),
    t("drawdown52w"),
    t("compositeScore"),
  ]);
  setText(".metrics article:nth-child(2) small", t("periodReturnHint"));
  setText(".signalsPanel .panelHeader h2", t("signals"));
  setText(".signalsPanel .panelHeader span", t("researchOnly"));
  setText(".tablePanel .panelHeader h2", t("recentTradingDays"));
  setAllText(".tablePanel thead th", [
    t("date"),
    "LRC Z-score",
    t("open"),
    t("high"),
    t("low"),
    t("close"),
    t("changePct"),
    "RSI",
    t("volume"),
  ]);

  if (!batchPayload) fields.batchStatus.textContent = t("batchIntro");
  setText("#batchForm label span", t("search"));
  setPlaceholder("#batchSearch", t("searchPlaceholder"));
  setText("#batchForm button", t("run"));
  setAllText(".batchSummary article > span", [
    t("source"),
    t("generatedAt"),
    t("resultCount"),
    t("lrcWindow"),
  ]);
  setClosestLabelText("#batchIndustryFilter", t("industry"));
  setOptionText("#batchIndustryFilter", "", t("allIndustries"));
  setAllText(".rangeFilter span", [t("to"), t("to"), t("to"), t("to")]);
  setClosestLegend("#batchMarketCapMin", t("marketCap"));
  setClosestLegend("#batchOperatingProfitMin", t("operatingProfitTtm"));
  setPlaceholder("#batchZMin", t("min"));
  setPlaceholder("#batchZMax", t("max"));
  setPlaceholder("#batchRsiMin", t("min"));
  setPlaceholder("#batchRsiMax", t("max"));
  setPlaceholder("#batchMarketCapMin", t("min"));
  setPlaceholder("#batchMarketCapMax", t("max"));
  setPlaceholder("#batchOperatingProfitMin", t("min"));
  setPlaceholder("#batchOperatingProfitMax", t("max"));
  setPriceRelation("#batchPriceMa20Relation", "MA20", t("priceMa20"));
  setPriceRelation("#batchPriceMa50Relation", "MA50", t("priceMa50"));
  setPriceRelation("#batchPriceMa200Relation", "MA200", t("priceMa200"));
  setClosestLabelText("#batchMa50Ma200Relation", "MA50 / MA200");
  setOptionText("#batchMa50Ma200Relation", "", t("anyRelation"));
  setOptionText("#batchMa50Ma200Relation", "above", t("ma50Above"));
  setOptionText("#batchMa50Ma200Relation", "below", t("ma50Below"));
  setOptionText("#batchMa50Ma200Relation", "equal", t("ma50Near"));
  setClosestLabelText("#batchShowErrors", t("showFailedRows"));
  setText("#batchClearFilters", t("clear"));
  setText(".tableHeader h2", t("screeningResults"));
  setText(".pageSizeControl span", t("perPage"));
  setAllText(".sortButton", [
    t("symbol"),
    "LRC Z-score",
    t("name"),
    t("latest"),
    t("changePct"),
    t("volume"),
    "MA20",
    "MA50",
    "MA200",
    "RSI14",
    t("industry"),
  ]);

  if (!maSlopePayload) {
    fields.maSlopeTitle.textContent = "MA Slope";
    fields.maSlopeStatus.textContent = t("maSlopeIntro");
  }
  setAllText("#maSlopeForm label span", [
    t("symbol"),
    t("displayPeriod"),
    t("maPeriods"),
    t("slopeLookback"),
    t("showVolume"),
    t("logPrice"),
  ]);
  setPeriodOptions("#maSlopePeriod");
  setText("#maSlopeForm button", t("analyze"));
  setText(".maSlopeCharts .chartPanel:nth-child(1) .panelHeader h2", t("priceAndMa"));
  setText(".maSlopeCharts .chartPanel:nth-child(2) .panelHeader span", t("percentPerDay"));
  const disclosures = document.querySelectorAll(".dataDisclosure");
  disclosures[0]?.querySelector("summary span")?.replaceChildren(t("slopeStatistics"));
  if (disclosures[1]) disclosures[1].querySelector("summary").textContent = t("rawData");
  setAllText(".maSlopeStatsTable thead th", [
    "MA",
    t("current"),
    t("mean"),
    t("stdDev"),
    t("min"),
    t("minDate"),
    t("max"),
    t("negativeDaysPct"),
  ]);
}

function setPeriodOptions(selector) {
  setOptionText(selector, "3mo", currentLanguage === "zh-Hant" ? "3 個月" : "3 months");
  setOptionText(selector, "6mo", currentLanguage === "zh-Hant" ? "6 個月" : "6 months");
  setOptionText(selector, "1y", currentLanguage === "zh-Hant" ? "1 年" : "1 year");
  setOptionText(selector, "2y", currentLanguage === "zh-Hant" ? "2 年" : "2 years");
  setOptionText(selector, "3y", currentLanguage === "zh-Hant" ? "3 年" : "3 years");
  setOptionText(selector, "5y", currentLanguage === "zh-Hant" ? "5 年" : "5 years");
  setOptionText(selector, "10y", currentLanguage === "zh-Hant" ? "10 年" : "10 years");
}

function setPriceRelation(selector, maLabel, label) {
  setClosestLabelText(selector, label);
  setOptionText(selector, "", t("anyRelation"));
  setOptionText(selector, "above", t("priceAbove", { ma: maLabel }));
  setOptionText(selector, "below", t("priceBelow", { ma: maLabel }));
  setOptionText(selector, "equal", t("priceNear", { ma: maLabel }));
}

function rerenderCurrentData() {
  if (currentAnalysisPayload) render(currentAnalysisPayload);
  if (batchPayload) {
    populateIndustryFilter(batchPayload.results || []);
    renderBatch(batchPayload);
  }
  if (maSlopePayload) renderMaSlope(maSlopePayload);
}

function showView(viewId) {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === viewId);
  });
  navButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewId);
  });
  const hashes = {
    batchView: "#batch",
    maSlopeView: "#ma-slope",
    singleView: "#single",
  };
  history.replaceState(null, "", hashes[viewId] || "#single");
  if (viewId === "batchView" && !window.batchLoaded) {
    loadBatch();
  }
  if (viewId === "singleView" && window.currentRows) {
    requestAnimationFrame(() => {
      drawChart(window.currentRows);
      if (window.currentLrc) drawLrcChart(window.currentLrc);
    });
  } else if (viewId === "singleView") {
    loadAnalysis();
  }
  if (viewId === "maSlopeView") {
    if (!maSlopePayload) {
      loadMaSlope();
    } else {
      requestAnimationFrame(() => {
        drawMaSlopePriceChart(maSlopePayload.rows);
        drawMaSlopeChart(maSlopePayload.rows);
      });
    }
  }
}

async function loadAnalysis() {
  const symbol = symbolInput.value.trim() || "AAPL";
  const period = periodInput.value;
  setLoading(true, t("loadingSymbol", { symbol: symbol.toUpperCase() }));
  try {
    const response = await fetch(`/api/analyze?symbol=${encodeURIComponent(symbol)}&period=${period}`);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || t("requestFailed"));
    render(payload);
    statusEl.textContent = t("analysisReady", { symbol: payload.symbol });
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
  fields.batchStatus.textContent = t("loadingBatch");
  fields.batchStatus.classList.remove("error");
  try {
    const response = await fetch(`/api/batch?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || t("batchRequestFailed"));
    batchPayload = payload;
    populateIndustryFilter(payload.results || []);
    batchPageIndex = 0;
    renderBatch(payload);
    window.batchLoaded = true;
    const filters = [
      payload.markets.length ? `markets=${payload.markets.join(",")}` : "",
    ].filter(Boolean).join("; ");
    fields.batchStatus.textContent = `${payload.symbolsFile} / ${sourceLabel(payload.source)}${filters ? ` / ${filters}` : ""}`;
  } catch (error) {
    fields.batchStatus.textContent = error.message;
    fields.batchStatus.classList.add("error");
  } finally {
    button.disabled = false;
  }
}

async function loadMaSlope() {
  const symbol = maSlopeSymbol.value.trim().toUpperCase() || "QQQ";
  const params = new URLSearchParams({
    symbol,
    period: maSlopePeriod.value,
    mas: maSlopePeriods.value,
    slopeWindow: maSlopeWindow.value,
  });
  const button = maSlopeForm.querySelector("button[type='submit']");
  button.disabled = true;
  fields.maSlopeStatus.textContent = t("calculatingSlope", { symbol });
  fields.maSlopeStatus.classList.remove("error");
  try {
    const response = await fetch(`/api/ma-slope?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || t("maSlopeRequestFailed"));
    maSlopePayload = payload;
    renderMaSlope(payload);
    fields.maSlopeStatus.textContent = t("tradingDays", { date: payload.latest.date, count: payload.rows.length });
  } catch (error) {
    fields.maSlopeStatus.textContent = error.message;
    fields.maSlopeStatus.classList.add("error");
  } finally {
    button.disabled = false;
  }
}

function renderMaSlope(payload) {
  fields.maSlopeTitle.textContent = [payload.symbol, payload.name, "MA Slope"].filter(Boolean).join(" ");
  fields.maSlopePriceHint.textContent = ["Close", ...payload.periods.map((period) => `MA${period}`)].join(" / ");
  fields.maSlopeChartTitle.textContent = t("slopeTitle", { days: payload.slopeWindow });
  maSlopeWindowValue.value = payload.slopeWindow;
  fields.maSlopeRange.textContent = t("dateRange", {
    start: payload.rows[0].date,
    end: payload.rows[payload.rows.length - 1].date,
  });
  fields.maSlopeMetrics.innerHTML = `
    <article>
      <span>${t("latestClose")}</span>
      <strong>${money(payload.latest.close)}</strong>
      <small>${escapeHtml(payload.latest.date)}</small>
    </article>
  `;
  for (const metric of payload.metrics) {
    const article = document.createElement("article");
    const slopeClass = trendClass(metric.slope);
    const priceVsMaClass = trendClass(metric.priceVsMaPct);
    article.innerHTML = `
      <span>MA${metric.period}</span>
      <strong class="${priceVsMaClass}">${numberOrDash(metric.ma, 2)}</strong>
      <small>${signedPctOrDash(metric.priceVsMaPct)} ${t("vsLatestPrice")}</small>
      <div class="metricDivider"></div>
      <span>${t("slope")}</span>
      <strong class="${slopeClass}">${signedNumberOrDash(metric.slope, 3)}${currentLanguage === "zh-Hant" ? "%/日" : "%/day"}</strong>
      <small>${numberOrDash(metric.percentile, 0)} ${t("percentile")}</small>
    `;
    fields.maSlopeMetrics.appendChild(article);
  }
  fields.maSlopeStatsBody.innerHTML = "";
  for (const statistic of payload.statistics) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>MA${statistic.period}</td>
      <td class="${numberValue(statistic.current) >= 0 ? "up" : "down"}">${signedNumberOrDash(statistic.current, 3)}</td>
      <td>${signedNumberOrDash(statistic.mean, 3)}</td>
      <td>${numberOrDash(statistic.stddev, 3)}</td>
      <td>${signedNumberOrDash(statistic.min, 3)}</td>
      <td>${escapeHtml(valueOrDash(statistic.minDate))}</td>
      <td>${signedNumberOrDash(statistic.max, 3)}</td>
      <td>${numberOrDash(statistic.negativePct, 1)}%</td>
    `;
    fields.maSlopeStatsBody.appendChild(row);
  }
  renderMaSlopeRawTable(payload);
  renderInteractiveLegend(
    fields.maSlopePriceLegend,
    [
      { key: "close", label: `${payload.symbol} Close`, color: "#17202a" },
      ...payload.periods.map((period, index) => ({
        key: String(period),
        label: `${period}DMA`,
        color: maSlopeColor(period, index),
      })),
    ],
    maSlopePriceHidden,
    () => drawMaSlopePriceChart(payload.rows),
  );
  renderInteractiveLegend(
    fields.maSlopeLegend,
    payload.periods.map((period, index) => ({
      key: String(period),
      label: `${period}DMA slope`,
      color: maSlopeColor(period, index),
    })),
    maSlopeHidden,
    () => drawMaSlopeChart(payload.rows),
  );
  drawMaSlopePriceChart(payload.rows);
  drawMaSlopeChart(payload.rows);
}

function renderMaSlopeRawTable(payload) {
  const periodHeaders = payload.periods.flatMap((period) => [
    `<th>SMA${period}</th>`,
    `<th>Slope${period}</th>`,
  ]).join("");
  fields.maSlopeRawHead.innerHTML = `
    <tr>
      <th>${t("date")}</th>
      <th>${t("open")}</th>
      <th>${t("high")}</th>
      <th>${t("low")}</th>
      <th>${t("close")}</th>
      <th>${t("volume")}</th>
      ${periodHeaders}
    </tr>
  `;
  fields.maSlopeRawBody.innerHTML = "";
  for (const item of payload.rows.slice(-30)) {
    const indicatorCells = payload.periods.flatMap((period) => [
      `<td>${numberOrDash(item.mas[String(period)], 2)}</td>`,
      `<td>${signedNumberOrDash(item.slopes[String(period)], 3)}</td>`,
    ]).join("");
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(item.date)}</td>
      <td>${numberOrDash(item.open, 2)}</td>
      <td>${numberOrDash(item.high, 2)}</td>
      <td>${numberOrDash(item.low, 2)}</td>
      <td>${numberOrDash(item.close, 2)}</td>
      <td>${compactOrDash(item.volume)}</td>
      ${indicatorCells}
    `;
    fields.maSlopeRawBody.appendChild(row);
  }
}

function renderInteractiveLegend(container, items, hidden, redraw) {
  const validKeys = new Set(items.map((item) => item.key));
  [...hidden].forEach((key) => {
    if (!validKeys.has(key)) hidden.delete(key);
  });
  container.innerHTML = "";
  for (const item of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `legendToggle${hidden.has(item.key) ? " muted" : ""}`;
    button.innerHTML = `<span class="legendLine" style="background:${item.color}"></span>${escapeHtml(item.label)}`;
    button.addEventListener("click", () => {
      if (hidden.has(item.key)) hidden.delete(item.key);
      else hidden.add(item.key);
      button.classList.toggle("muted", hidden.has(item.key));
      redraw();
    });
    container.appendChild(button);
  }
}

function render(payload) {
  currentAnalysisPayload = payload;
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
  fields.scoreLabel.textContent = localizeScoreLabel(payload.score.label);
  fields.analysisTitle.textContent = [payload.symbol, payload.name].filter(Boolean).join(" ");
  fields.chartTitle.textContent = `${payload.symbol} ${t("priceTrend")}`;
  fields.rowCount.textContent = t("rows", { count: payload.rows.length });
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
        <span>${escapeHtml(localizeSignalValue(signal.value))}</span>
      </div>
      <small>${escapeHtml(localizeSignalDetail(signal.detail))}</small>
    `;
    node.querySelector("strong").textContent = localizeSignalLabel(signal.label);
    fields.signals.appendChild(node);
  }
}

function renderHistoryPage() {
  const pageCount = Math.max(1, Math.ceil(historyRows.length / HISTORY_PAGE_SIZE));
  const start = historyPageIndex * HISTORY_PAGE_SIZE;
  renderTable(historyRows.slice(start, start + HISTORY_PAGE_SIZE));
  fields.rowCount.textContent = t("rows", { count: historyRows.length });
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
      <td class="${zScoreClass(row.lrc_zscore)}">${numberOrDash(row.lrc_zscore, 2)}</td>
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
  fields.batchSource.textContent = sourceLabel(payload.source);
  fields.batchGenerated.textContent = payload.generatedAt ? formatDateTime(payload.generatedAt) : "-";
  const allRows = payload.results || [];
  const okCount = allRows.filter((row) => row.ok).length;
  const failCount = allRows.length - okCount;
  const filteredRows = filterBatchRows(payload.results || []);
  const sortedRows = sortBatchRows(filteredRows);
  const pageSize = Number(batchPageSize.value);
  const pageCount = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  batchPageIndex = Math.min(batchPageIndex, pageCount - 1);
  const start = batchPageIndex * pageSize;
  const pageRows = sortedRows.slice(start, start + pageSize);
  fields.batchCount.textContent = failCount ? `${okCount} / ${allRows.length}` : okCount;
  fields.batchRowCount.textContent = t("rows", { count: filteredRows.length });
  fields.batchPage.textContent = `${batchPageIndex + 1} / ${pageCount}`;
  fields.batchWindow.textContent = t("days", { count: payload.window || 200 });
  prevBatchPage.disabled = batchPageIndex === 0;
  nextBatchPage.disabled = batchPageIndex >= pageCount - 1;
  updateSortButtons();
  if (!pageRows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="11" class="emptyCell">${t("noMatches")}</td>`;
    fields.batchBody.appendChild(tr);
    return;
  }
  for (const row of pageRows) {
    const tr = document.createElement("tr");
    if (row.ok) {
      const rowFields = row.fields || {};
      tr.className = "clickableRow";
      tr.title = t("openSingle");
      tr.addEventListener("click", () => openSingleStock(row.symbol));
      tr.innerHTML = `
        <td>${escapeHtml(valueOrDash(rowFields["代碼"] || row.symbol))}</td>
        <td class="${row.zScore >= 0 ? "up" : "down"}">${numberOrDash(rowFields["LRC Z-score"], 2)}</td>
        <td class="stockNameCell" title="${escapeHtml(valueOrDash(rowFields["名稱"]))}">${escapeHtml(valueOrDash(rowFields["名稱"]))}</td>
        <td>${numberOrDash(rowFields["最新價"], 2)}</td>
        <td class="${Number(rowFields["漲跌幅"]) >= 0 ? "up" : "down"}">${percentOrDash(rowFields["漲跌幅"])}</td>
        <td>${compactOrDash(rowFields["成交量"])}</td>
        <td>${numberOrDash(rowFields["MA-MA20-日線"], 2)}</td>
        <td>${numberOrDash(rowFields["MA-MA50-日線"], 2)}</td>
        <td>${numberOrDash(rowFields["MA-MA200-日線"], 2)}</td>
        <td>${numberOrDash(rowFields["RSI-RSI14-日線"], 1)}</td>
        <td>${escapeHtml(valueOrDash(rowFields["所屬行業"]))}</td>
      `;
    } else {
      tr.innerHTML = `
        <td>${escapeHtml(row.symbol)}</td>
        <td colspan="9">-</td>
        <td class="error">${escapeHtml(row.error)}</td>
      `;
    }
    fields.batchBody.appendChild(tr);
  }
}

function filterBatchRows(rows) {
  const query = batchSearch.value.trim().toUpperCase();
  const showErrors = batchShowErrors.checked;
  const industry = batchIndustryFilter.value;
  const priceMa20Relation = document.querySelector("#batchPriceMa20Relation").value;
  const priceMa50Relation = document.querySelector("#batchPriceMa50Relation").value;
  const priceMa200Relation = document.querySelector("#batchPriceMa200Relation").value;
  const ma50Ma200Relation = document.querySelector("#batchMa50Ma200Relation").value;
  const zMin = numberInputValue("#batchZMin");
  const zMax = numberInputValue("#batchZMax");
  const rsiMin = numberInputValue("#batchRsiMin");
  const rsiMax = numberInputValue("#batchRsiMax");
  const marketCapMin = numberInputValue("#batchMarketCapMin");
  const marketCapMax = numberInputValue("#batchMarketCapMax");
  const operatingProfitMin = numberInputValue("#batchOperatingProfitMin");
  const operatingProfitMax = numberInputValue("#batchOperatingProfitMax");
  return rows.filter((row) => {
    if (!showErrors && !row.ok) return false;
    const rowFields = row.fields || {};
    const rowIndustry = valueOrDash(rowFields["所屬行業"]);
    const zScore = numberValue(rowFields["LRC Z-score"] ?? row.zScore);
    const rsi14 = numberValue(rowFields["RSI-RSI14-日線"]);
    const marketCap = numberValue(rowFields["市值"]);
    const price = numberValue(rowFields["最新價"]);
    const ma20 = numberValue(rowFields["MA-MA20-日線"]);
    const ma50 = numberValue(rowFields["MA-MA50-日線"]);
    const ma200 = numberValue(rowFields["MA-MA200-日線"]);
    const operatingProfit = numberValue(rowFields["營業利潤(TTM)"]);
    const matchesQuery = !query || [
      row.symbol,
      rowFields["代碼"],
      rowFields["名稱"],
      rowIndustry,
    ].some((value) => String(value || "").toUpperCase().includes(query));
    return matchesQuery
      && (!industry || rowIndustry === industry)
      && inRange(zScore, zMin, zMax)
      && inRange(rsi14, rsiMin, rsiMax)
      && inRange(marketCap, marketCapMin, marketCapMax)
      && inRange(operatingProfit, operatingProfitMin, operatingProfitMax)
      && matchesPriceMaRelation(price, ma20, priceMa20Relation)
      && matchesPriceMaRelation(price, ma50, priceMa50Relation)
      && matchesPriceMaRelation(price, ma200, priceMa200Relation)
      && matchesPriceMaRelation(ma50, ma200, ma50Ma200Relation);
  });
}

function sortBatchRows(rows) {
  const direction = batchSort.direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => compareBatchRows(a, b, batchSort.key) * direction);
}

function compareBatchRows(a, b, key) {
  const aValue = batchSortValue(a, key);
  const bValue = batchSortValue(b, key);
  if (aValue === null && bValue === null) return 0;
  if (aValue === null) return 1;
  if (bValue === null) return -1;
  if (typeof aValue === "number" && typeof bValue === "number") {
    return aValue - bValue;
  }
  return String(aValue).localeCompare(String(bValue), undefined, { numeric: true, sensitivity: "base" });
}

function batchSortValue(row, key) {
  const rowFields = row.fields || {};
  const values = {
    symbol: rowFields["代碼"] || row.symbol,
    zScore: rowFields["LRC Z-score"] ?? row.zScore,
    name: rowFields["名稱"],
    price: rowFields["最新價"],
    changePct: rowFields["漲跌幅"],
    volume: rowFields["成交量"],
    ma20: rowFields["MA-MA20-日線"],
    ma50: rowFields["MA-MA50-日線"],
    ma200: rowFields["MA-MA200-日線"],
    rsi14: rowFields["RSI-RSI14-日線"],
    industry: rowFields["所屬行業"],
  };
  if (["zScore", "price", "changePct", "volume", "ma20", "ma50", "ma200", "rsi14"].includes(key)) {
    return numberValue(values[key]);
  }
  const value = values[key];
  return value === null || value === undefined || value === "" ? null : String(value);
}

function populateIndustryFilter(rows) {
  const selected = batchIndustryFilter.value;
  const industries = [...new Set(rows.map((row) => row.fields?.["所屬行業"]).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), undefined, { sensitivity: "base" }));
  batchIndustryFilter.innerHTML = `<option value="">${t("allIndustries")}</option>`;
  for (const industry of industries) {
    const option = document.createElement("option");
    option.value = industry;
    option.textContent = industry;
    batchIndustryFilter.appendChild(option);
  }
  batchIndustryFilter.value = industries.includes(selected) ? selected : "";
}

function updateSortButtons() {
  sortButtons.forEach((button) => {
    const active = button.dataset.sort === batchSort.key;
    button.classList.toggle("active", active);
    button.dataset.direction = active ? batchSort.direction : "";
  });
}

function numberInputValue(selector) {
  const value = document.querySelector(selector).value;
  return value === "" ? null : Number(value);
}

function numberValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function trendClass(value) {
  const number = numberValue(value);
  if (number === null || number === 0) return "";
  return number > 0 ? "up" : "down";
}

function inRange(value, min, max) {
  if (value === null) return min === null && max === null;
  return (min === null || value >= min) && (max === null || value <= max);
}

function matchesPriceMaRelation(price, movingAverage, relation) {
  if (!relation) return true;
  if (price === null || movingAverage === null) return false;
  const tolerance = Math.max(Math.abs(movingAverage) * 0.005, 0.01);
  if (relation === "above") return price > movingAverage + tolerance;
  if (relation === "below") return price < movingAverage - tolerance;
  return Math.abs(price - movingAverage) <= tolerance;
}

function openSingleStock(symbol) {
  const hadRows = Boolean(window.currentRows);
  symbolInput.value = symbol;
  maSlopeSymbol.value = symbol;
  if (maSlopePayload?.symbol !== symbol) {
    maSlopePayload = null;
  }
  showView("singleView");
  if (hadRows) loadAnalysis();
}

function drawMaSlopePriceChart(rows, hoverIndex = null) {
  const ratio = window.devicePixelRatio || 1;
  const rect = maSlopePriceCanvas.getBoundingClientRect();
  maSlopePriceCanvas.width = Math.floor(rect.width * ratio);
  maSlopePriceCanvas.height = Math.floor(rect.height * ratio);
  maSlopePriceCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const width = rect.width;
  const height = rect.height;
  const showVolume = maSlopeVolume.checked;
  const pad = { top: 28, right: 62, bottom: showVolume ? 104 : 36, left: 52 };
  maSlopePriceCtx.clearRect(0, 0, width, height);
  if (!rows.length || !maSlopePayload) return;

  const periods = maSlopePayload.periods;
  const visiblePeriods = periods.filter((period) => !maSlopePriceHidden.has(String(period)));
  const showClose = !maSlopePriceHidden.has("close");
  const priceValues = rows.flatMap((row) => [
    ...(showClose ? [row.close] : []),
    ...visiblePeriods.map((period) => row.mas[String(period)]),
  ]).filter((value) => value != null && (!maSlopeLogScale.checked || value > 0));
  if (!priceValues.length) {
    drawEmptyChartMessage(maSlopePriceCtx, t("selectPriceLine"));
    return;
  }
  const rawMin = Math.min(...priceValues);
  const rawMax = Math.max(...priceValues);
  const transform = maSlopeLogScale.checked ? Math.log : (value) => value;
  const transformedMin = transform(rawMin);
  const transformedMax = transform(rawMax);
  const span = Math.max(transformedMax - transformedMin, 0.000001);
  const x = (idx) => pad.left + (idx / Math.max(rows.length - 1, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((transformedMax - transform(value)) / span) * (height - pad.top - pad.bottom);

  drawContextGrid(maSlopePriceCtx, width, height, pad, rawMin, rawMax, y);
  if (showClose) {
    drawContextLine(maSlopePriceCtx, rows.map((row) => row.close), x, y, "#17202a", 2.2);
  }
  visiblePeriods.forEach((period) => {
    const index = periods.indexOf(period);
    drawContextLine(
      maSlopePriceCtx,
      rows.map((row) => row.mas[String(period)]),
      x,
      y,
      maSlopeColor(period, index),
      1.7,
    );
  });
  if (showVolume) {
    drawMaSlopeVolume(rows, x, width, height, pad);
  }
  if (hoverIndex !== null) {
    drawMaSlopeHover(
      maSlopePriceCtx,
      rows,
      hoverIndex,
      x,
      y,
      pad,
      height,
      [...(showClose ? ["close"] : []), ...visiblePeriods],
      false,
    );
  }
}

function drawMaSlopeChart(rows, hoverIndex = null) {
  const ratio = window.devicePixelRatio || 1;
  const rect = maSlopeCanvas.getBoundingClientRect();
  maSlopeCanvas.width = Math.floor(rect.width * ratio);
  maSlopeCanvas.height = Math.floor(rect.height * ratio);
  maSlopeCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const width = rect.width;
  const height = rect.height;
  const pad = { top: 28, right: 62, bottom: 36, left: 52 };
  maSlopeCtx.clearRect(0, 0, width, height);
  if (!rows.length || !maSlopePayload) return;

  const periods = maSlopePayload.periods;
  const visiblePeriods = periods.filter((period) => !maSlopeHidden.has(String(period)));
  const values = rows.flatMap((row) => visiblePeriods.map((period) => row.slopes[String(period)]))
    .filter((value) => value != null);
  if (!values.length) {
    drawEmptyChartMessage(maSlopeCtx, t("selectSlopeLine"));
    return;
  }
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = Math.max(max - min, 0.000001);
  const x = (idx) => pad.left + (idx / Math.max(rows.length - 1, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((max - value) / span) * (height - pad.top - pad.bottom);

  drawContextGrid(maSlopeCtx, width, height, pad, min, max, y, 3);
  maSlopeCtx.save();
  maSlopeCtx.strokeStyle = "#7b8794";
  maSlopeCtx.setLineDash([5, 4]);
  maSlopeCtx.beginPath();
  maSlopeCtx.moveTo(pad.left, y(0));
  maSlopeCtx.lineTo(width - pad.right, y(0));
  maSlopeCtx.stroke();
  maSlopeCtx.restore();
  visiblePeriods.forEach((period) => {
    const index = periods.indexOf(period);
    drawContextLine(
      maSlopeCtx,
      rows.map((row) => row.slopes[String(period)]),
      x,
      y,
      maSlopeColor(period, index),
      1.8,
    );
  });
  if (hoverIndex !== null) {
    drawMaSlopeHover(maSlopeCtx, rows, hoverIndex, x, y, pad, height, visiblePeriods, true);
  }
}

function drawEmptyChartMessage(context, message) {
  context.fillStyle = "#5e6b78";
  context.font = "13px Segoe UI, Arial";
  context.fillText(message, 52, 42);
}

function drawContextGrid(context, width, height, pad, min, max, y, digits = 2) {
  context.strokeStyle = "#e5eaf0";
  context.fillStyle = "#5e6b78";
  context.lineWidth = 1;
  context.font = "12px Segoe UI, Arial";
  for (let index = 0; index <= 4; index += 1) {
    const value = min + ((max - min) * index) / 4;
    const lineY = y(value);
    context.beginPath();
    context.moveTo(pad.left, lineY);
    context.lineTo(width - pad.right, lineY);
    context.stroke();
    context.fillText(value.toFixed(digits), width - pad.right + 8, lineY + 4);
  }
  context.strokeStyle = "#cbd5df";
  context.strokeRect(pad.left, pad.top, width - pad.left - pad.right, height - pad.top - pad.bottom);
}

function drawContextLine(context, values, x, y, color, lineWidth) {
  context.beginPath();
  context.strokeStyle = color;
  context.lineWidth = lineWidth;
  let started = false;
  values.forEach((value, index) => {
    if (value == null) {
      started = false;
      return;
    }
    if (!started) {
      context.moveTo(x(index), y(value));
      started = true;
    } else {
      context.lineTo(x(index), y(value));
    }
  });
  context.stroke();
}

function drawMaSlopeVolume(rows, x, width, height, pad) {
  const maxVolume = Math.max(...rows.map((row) => Number(row.volume) || 0), 1);
  const top = height - pad.bottom + 24;
  const bottom = height - 26;
  const barWidth = Math.max(1, (width - pad.left - pad.right) / rows.length * 0.72);
  maSlopePriceCtx.fillStyle = "#cbd5df";
  rows.forEach((row, index) => {
    const barHeight = ((Number(row.volume) || 0) / maxVolume) * (bottom - top);
    maSlopePriceCtx.fillRect(x(index) - barWidth / 2, bottom - barHeight, barWidth, barHeight);
  });
  maSlopePriceCtx.fillStyle = "#5e6b78";
  maSlopePriceCtx.font = "12px Segoe UI, Arial";
  maSlopePriceCtx.fillText(t("volume"), pad.left, top - 6);
}

function drawMaSlopeHover(context, rows, index, x, y, pad, height, series, slope) {
  const lineX = x(index);
  context.save();
  context.strokeStyle = "#7b8794";
  context.setLineDash([4, 4]);
  context.beginPath();
  context.moveTo(lineX, pad.top);
  context.lineTo(lineX, height - pad.bottom);
  context.stroke();
  context.setLineDash([]);
  series.forEach((key) => {
    const value = key === "close"
      ? rows[index].close
      : rows[index][slope ? "slopes" : "mas"][String(key)];
    if (value == null) return;
    context.beginPath();
    context.arc(lineX, y(value), 3.5, 0, Math.PI * 2);
    const periodIndex = maSlopePayload?.periods.indexOf(Number(key)) ?? 0;
    context.fillStyle = key === "close" ? "#17202a" : maSlopeColor(key, periodIndex);
    context.fill();
    context.strokeStyle = "#ffffff";
    context.stroke();
  });
  context.restore();
}

function maSlopeColor(period, index) {
  const canonical = {
    20: "#2563eb",
    50: "#d97706",
    200: "#dc2626",
  };
  const palette = ["#0f766e", "#7c3aed", "#0891b2", "#be123c", "#4d7c0f"];
  return canonical[period] || palette[index % palette.length];
}

function drawChart(rows, hoverIndex = null) {
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
  if (hoverIndex !== null) {
    drawHoverGuide(ctx, hoverIndex, rows, x, y, pad, height, ["close", "sma20", "sma50"]);
  }
}

function drawLrcChart(rows, hoverIndex = null) {
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
    lrcCtx.fillText(t("notEnoughLrc"), pad.left, pad.top + 16);
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
  if (hoverIndex !== null) {
    drawHoverGuide(lrcCtx, hoverIndex, rows, x, y, pad, height, ["close", "trend"]);
  }
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

function bindChartTooltip(chart, tooltip, rowsProvider, draw, content) {
  chart.addEventListener("mousemove", (event) => {
    const rows = rowsProvider();
    if (!rows.length) return;
    const rect = chart.getBoundingClientRect();
    const pad = { left: 48, right: 58 };
    const plotWidth = rect.width - pad.left - pad.right;
    const plotX = event.clientX - rect.left;
    if (plotX < pad.left || plotX > rect.width - pad.right) {
      hideChartTooltip(tooltip, draw, rows);
      return;
    }
    const index = Math.max(
      0,
      Math.min(rows.length - 1, Math.round(((plotX - pad.left) / plotWidth) * (rows.length - 1))),
    );
    draw(rows, index);
    tooltip.innerHTML = content(rows[index]);
    tooltip.hidden = false;
    const tooltipLeft = Math.min(Math.max(event.clientX - rect.left + 12, 8), rect.width - 190);
    const tooltipTop = Math.max(event.clientY - rect.top - 14, 8);
    tooltip.style.left = `${tooltipLeft}px`;
    tooltip.style.top = `${tooltipTop}px`;
  });
  chart.addEventListener("mouseleave", () => {
    hideChartTooltip(tooltip, draw, rowsProvider());
  });
}

function hideChartTooltip(tooltip, draw, rows) {
  tooltip.hidden = true;
  if (rows.length) draw(rows);
}

function drawHoverGuide(context, index, rows, x, y, pad, height, keys) {
  const colors = ["#17202a", "#0f766e", "#2563eb"];
  const lineX = x(index);
  context.save();
  context.strokeStyle = "#7b8794";
  context.lineWidth = 1;
  context.setLineDash([4, 4]);
  context.beginPath();
  context.moveTo(lineX, pad.top);
  context.lineTo(lineX, height - pad.bottom);
  context.stroke();
  context.setLineDash([]);
  keys.forEach((key, colorIndex) => {
    const value = numberValue(rows[index][key]);
    if (value === null) return;
    context.beginPath();
    context.arc(lineX, y(value), 3.5, 0, Math.PI * 2);
    context.fillStyle = colors[colorIndex] || "#2563eb";
    context.fill();
    context.strokeStyle = "#ffffff";
    context.lineWidth = 1.5;
    context.stroke();
  });
  context.restore();
}

function priceTooltipHtml(row) {
  return `
    <strong>${escapeHtml(row.date)}</strong>
    <span>${t("close")} ${numberOrDash(row.close, 2)}</span>
    <span>MA20 ${numberOrDash(row.sma20, 2)}</span>
    <span>MA50 ${numberOrDash(row.sma50, 2)}</span>
  `;
}

function lrcTooltipHtml(row) {
  const stddev = (numberValue(row.upper2) - numberValue(row.trend)) / 2;
  const zScore = stddev ? (numberValue(row.close) - numberValue(row.trend)) / stddev : null;
  return `
    <strong>${escapeHtml(row.date)}</strong>
    <span>${t("close")} ${numberOrDash(row.close, 2)}</span>
    <span>${currentLanguage === "zh-Hant" ? "趨勢" : "Trend"} ${numberOrDash(row.trend, 2)}</span>
    <span>+2σ ${numberOrDash(row.upper2, 2)}</span>
    <span>-2σ ${numberOrDash(row.lower2, 2)}</span>
    <span>Z-score ${numberOrDash(zScore, 2)}</span>
  `;
}

function maSlopePriceTooltipHtml(row) {
  const maLines = (maSlopePayload?.periods || [])
    .filter((period) => !maSlopePriceHidden.has(String(period)))
    .map((period) => `<span>MA${period} ${numberOrDash(row.mas[String(period)], 2)}</span>`)
    .join("");
  return `
    <strong>${escapeHtml(row.date)}</strong>
    ${maSlopePriceHidden.has("close") ? "" : `<span>${t("close")} ${numberOrDash(row.close, 2)}</span>`}
    ${maLines}
    ${maSlopeVolume.checked ? `<span>${t("volume")} ${compactOrDash(row.volume)}</span>` : ""}
  `;
}

function maSlopeTooltipHtml(row) {
  const slopeLines = (maSlopePayload?.periods || [])
    .filter((period) => !maSlopeHidden.has(String(period)))
    .map((period) => `<span>MA${period} ${signedNumberOrDash(row.slopes[String(period)], 3)}${currentLanguage === "zh-Hant" ? "%/日" : "%/day"}</span>`)
    .join("");
  return `
    <strong>${escapeHtml(row.date)}</strong>
    ${slopeLines}
  `;
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

function zScoreClass(value) {
  if (value === null || value === undefined || value === "") return "";
  return Number(value) >= 0 ? "up" : "down";
}

function percentOrDash(value) {
  if (value === null || value === undefined || value === "") return "-";
  return pct(value);
}

function compactOrDash(value) {
  if (value === null || value === undefined || value === "") return "-";
  return compact(value);
}

function signedNumberOrDash(value, digits = 2) {
  const number = numberValue(value);
  if (number === null) return "-";
  return `${number >= 0 ? "+" : ""}${number.toFixed(digits)}`;
}

function signedPctOrDash(value) {
  const number = numberValue(value);
  return number === null ? "-" : `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
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

function sourceLabel(source) {
  return source === "live" ? t("live") : t("precomputed");
}

function localizeScoreLabel(value) {
  const labels = {
    "Strong watch": t("strongWatch"),
    "Moderately strong": t("moderatelyStrong"),
    Neutral: t("neutral"),
    Weak: t("weak"),
  };
  return labels[value] || value;
}

function localizeSignalLabel(value) {
  const labels = {
    "Short/Mid-Term Trend": t("shortMidTrend"),
    "Long-Term Position": t("longTermPosition"),
    "RSI(14)": "RSI(14)",
    Volume: t("volume"),
    "52W Range": currentLanguage === "zh-Hant" ? "52週區間" : "52W Range",
  };
  return labels[value] || value;
}

function localizeSignalValue(value) {
  const labels = {
    "Bullish alignment": t("bullishAlignment"),
    "Not confirmed": t("notConfirmed"),
    "Above 200-day MA": t("above200"),
    "Below 200-day MA": t("below200"),
    Hot: t("hot"),
    Cold: t("cold"),
    Neutral: t("neutral"),
    Elevated: t("elevated"),
    Normal: t("normal"),
    "Near high": t("nearHigh"),
    "Near low": t("nearLow"),
    "Mid range": t("midRange"),
  };
  return labels[value] || value;
}

function localizeSignalDetail(value) {
  if (currentLanguage !== "zh-Hant") return value;
  let match = value.match(/^Close ([\d.-]+), 20-day MA ([\d.-]+), 50-day MA ([\d.-]+)$/);
  if (match) {
    return t("maDetail", { close: match[1], ma20: match[2], ma50: match[3] });
  }
  match = value.match(/^200-day MA ([\d.-]+)$/);
  if (match) {
    return t("ma200Detail", { value: match[1] });
  }
  match = value.match(/^Current RSI ([\d.-]+)$/);
  if (match) {
    return t("currentRsi", { value: match[1] });
  }
  match = value.match(/^Latest volume is ([\d.-]+)x the 20-day average$/);
  if (match) {
    return t("volumeDetail", { value: match[1] });
  }
  match = value.match(/^([+\-\d.]+)% from the 52-week high$/);
  if (match) {
    return t("drawdownDetail", { value: match[1] });
  }
  return value;
}

function batchLabel(zScore) {
  if (zScore <= -2) return t("belowMinus2");
  if (zScore <= -1) return t("lowLabel");
  if (zScore >= 2) return t("abovePlus2");
  if (zScore >= 1) return t("highLabel");
  return t("neutral");
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
