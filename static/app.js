"use strict";

const persianNumber = new Intl.NumberFormat("fa-IR");

const tagLabels = {
  V: "فعل",
  Inf: "مصدر",
  Part: "صفت مفعولی",
  Past: "گذشته",
  Pres: "حال",
  Fut: "آینده",
  Ind: "اخباری",
  Subj: "التزامی",
  Imp: "امری",
  Prog: "استمراری",
  Perf: "کامل",
  Neg: "منفی",
  Caus: "سببی",
  P1: "شخص اول",
  P2: "شخص دوم",
  P3: "شخص سوم",
  Sg: "مفرد",
  Pl: "جمع",
};

const analyzeForm = document.querySelector("#analyze-form");
const generateForm = document.querySelector("#generate-form");
const wordInput = document.querySelector("#word");
const analysisInput = document.querySelector("#analysis");
const normalizeInput = document.querySelector("#normalize-input");
const analyzeResponse = document.querySelector("#analyze-response");
const generateResponse = document.querySelector("#generate-response");
const serviceState = document.querySelector("#service-state");
const serviceStateLabel = document.querySelector("#service-state-label");
const appVersion = document.querySelector("#app-version");
const tabs = [...document.querySelectorAll("[role='tab']")];

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function setBusy(container, form, message) {
  container.setAttribute("aria-busy", "true");
  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  container.replaceChildren();

  const state = element("div", "loading-state");
  state.append(element("span"));
  state.append(element("p", "", message));
  container.append(state);
}

function clearBusy(container, form) {
  container.setAttribute("aria-busy", "false");
  form.querySelector("button[type='submit']").disabled = false;
}

function errorMessage(payload, fallback) {
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }
  if (payload?.detail?.message) {
    return payload.detail.message;
  }
  if (Array.isArray(payload?.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg;
  }
  return fallback;
}

function showError(container, message) {
  container.replaceChildren();
  const state = element("div", "error-state");
  state.append(element("span", "empty-glyph", "!"));
  state.append(element("h3", "", "درخواست انجام نشد"));
  state.append(element("p", "", message));
  container.append(state);
}

function showNoResults(container, title, message) {
  container.replaceChildren();
  const state = element("div", "no-results");
  state.append(element("span", "empty-glyph", "∅"));
  state.append(element("h3", "", title));
  state.append(element("p", "", message));
  container.append(state);
}

async function requestJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(errorMessage(payload, `HTTP ${response.status}`));
  }
  return payload;
}

async function copyText(value, button) {
  try {
    await navigator.clipboard.writeText(value);
    const previous = button.textContent;
    button.textContent = "رونوشت شد";
    window.setTimeout(() => {
      button.textContent = previous;
    }, 1200);
  } catch {
    button.textContent = "ناموفق";
  }
}

function createCopyButton(value) {
  const button = element("button", "copy-button", "رونوشت");
  button.type = "button";
  button.setAttribute("aria-label", "رونوشت تحلیل");
  button.addEventListener("click", () => copyText(value, button));
  return button;
}

function createTag(rawTag, isRoot = false) {
  const tag = element("span", `tag${isRoot ? " root-tag" : ""}`);
  const technical = element("b", "", isRoot ? `√${rawTag}` : rawTag);
  technical.dir = isRoot ? "rtl" : "ltr";
  tag.append(technical);

  let label = isRoot ? "ریشه" : tagLabels[rawTag];
  if (rawTag.startsWith("PV=")) {
    label = `پیش‌فعل: ${rawTag.slice(3)}`;
  }
  if (label) {
    tag.append(element("span", "", label));
  }
  return tag;
}

function createAnalysisCard(result, index) {
  const card = element("article", "analysis-card");
  const head = element("div", "analysis-card-head");
  head.append(
    element("span", "analysis-index", `خوانش ${persianNumber.format(index + 1)}`),
    createCopyButton(result.value),
  );

  const code = element("code", "analysis-code", result.value);
  code.dir = "ltr";

  const tags = element("div", "tag-list");
  tags.setAttribute("aria-label", "اجزای تحلیل");
  result.value.split("+").forEach((tag, tagIndex) => {
    tags.append(createTag(tag, tagIndex === 0));
  });

  const weight = element("div", "weight", `weight ${result.weight}`);
  weight.dir = "ltr";
  card.append(head, code, tags, weight);
  return card;
}

function renderAnalyses(payload) {
  if (!payload.analyses.length) {
    showNoResults(
      analyzeResponse,
      "تحلیلی پیدا نشد",
      "این صورت در پوشش فعلیِ دستور و واژه‌نامه نیست.",
    );
    return;
  }

  analyzeResponse.replaceChildren();
  const summary = element("div", "result-summary");
  const summaryCopy = element("div");
  summaryCopy.append(
    element("h3", "", `${persianNumber.format(payload.count)} تحلیل یافت شد`),
    element("p", "", "هر خوانش یک مسیر مستقل در تحلیل‌گر متناهی‌حال است."),
  );
  summary.append(summaryCopy);
  analyzeResponse.append(summary);

  if (payload.input !== payload.normalized) {
    const normalized = element(
      "p",
      "normalized-note",
      `ورودی معیارشده: ${payload.normalized}`,
    );
    normalized.dir = "auto";
    analyzeResponse.append(normalized);
  }

  if (payload.truncated) {
    analyzeResponse.append(
      element("p", "truncated-note", "نتایج به سقف درخواستی محدود شده‌اند."),
    );
  }

  const list = element("div", "result-list");
  payload.analyses.forEach((result, index) => {
    list.append(createAnalysisCard(result, index));
  });
  analyzeResponse.append(list);
}

function createFormCard(result, index) {
  const card = element("article", "form-card");
  const form = element("p", "generated-form", result.value);
  form.dir = "rtl";

  const meta = element("div", "form-meta");
  meta.append(
    element("span", "analysis-index", `صورت ${persianNumber.format(index + 1)}`),
    createCopyButton(result.value),
  );
  card.append(form, meta);
  return card;
}

function renderForms(payload) {
  if (!payload.forms.length) {
    showNoResults(
      generateResponse,
      "صورتی تولید نشد",
      "ترتیب یا ترکیب برچسب‌ها در دستور فعلی مجاز نیست.",
    );
    return;
  }

  generateResponse.replaceChildren();
  const summary = element("div", "result-summary");
  const summaryCopy = element("div");
  summaryCopy.append(
    element("h3", "", `${persianNumber.format(payload.count)} صورت تولید شد`),
    element("p", "", "خروجی واژگانی و واجیِ رشتهٔ تحلیل."),
  );
  summary.append(summaryCopy);
  generateResponse.append(summary);

  if (payload.truncated) {
    generateResponse.append(
      element("p", "truncated-note", "نتایج به سقف درخواستی محدود شده‌اند."),
    );
  }

  const list = element("div", "result-list");
  payload.forms.forEach((result, index) => {
    list.append(createFormCard(result, index));
  });
  generateResponse.append(list);
}

analyzeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = wordInput.value;
  if (!text.trim()) {
    showError(analyzeResponse, "یک صورت فعلی وارد کنید.");
    wordInput.focus();
    return;
  }

  setBusy(analyzeResponse, analyzeForm, "در حال پیمایش تحلیل‌گر…");
  try {
    const payload = await requestJson("/api/analyze", {
      text,
      normalize_input: normalizeInput.checked,
      max_analyses: 100,
    });
    renderAnalyses(payload);
  } catch (error) {
    showError(analyzeResponse, error.message || "خطای ناشناخته");
  } finally {
    clearBusy(analyzeResponse, analyzeForm);
  }
});

generateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const analysis = analysisInput.value;
  if (!analysis.trim()) {
    showError(generateResponse, "یک رشتهٔ تحلیل وارد کنید.");
    analysisInput.focus();
    return;
  }

  setBusy(generateResponse, generateForm, "در حال پیمایش صورت‌ساز…");
  try {
    const payload = await requestJson("/api/generate", {
      analysis,
      max_forms: 100,
    });
    renderForms(payload);
  } catch (error) {
    showError(generateResponse, error.message || "خطای ناشناخته");
  } finally {
    clearBusy(generateResponse, generateForm);
  }
});

document.querySelectorAll("[data-analyze-example]").forEach((button) => {
  button.addEventListener("click", () => {
    wordInput.value = button.dataset.analyzeExample;
    wordInput.focus();
  });
});

document.querySelectorAll("[data-generate-example]").forEach((button) => {
  button.addEventListener("click", () => {
    analysisInput.value = button.dataset.generateExample;
    analysisInput.focus();
  });
});

function activateTab(name) {
  tabs.forEach((tab) => {
    const isActive = tab.dataset.tab === name;
    tab.classList.toggle("is-active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
    tab.tabIndex = isActive ? 0 : -1;
    document.querySelector(`#${tab.getAttribute("aria-controls")}`).hidden = !isActive;
  });
}

tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => activateTab(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    let nextIndex;
    if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = tabs.length - 1;
    } else {
      const direction = event.key === "ArrowLeft" ? 1 : -1;
      nextIndex = (index + direction + tabs.length) % tabs.length;
    }
    activateTab(tabs[nextIndex].dataset.tab);
    tabs[nextIndex].focus();
  });
});

async function checkService() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    serviceState.classList.add("is-online");
    serviceStateLabel.textContent = "سامانه آماده است";
    appVersion.textContent = payload.version;
  } catch {
    serviceState.classList.add("is-offline");
    serviceStateLabel.textContent = "سامانه در دسترس نیست";
  }
}

checkService();
