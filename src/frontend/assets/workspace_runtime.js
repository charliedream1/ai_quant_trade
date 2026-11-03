
() => {
  if (window.__aiQuantRuntimeStarted) return;
  window.__aiQuantRuntimeStarted = true;
  __AI_CONSOLE_RUNTIME__
  const THEME_STORAGE_KEY = "all-in-one-ui-theme";
  const CONFIGURED_THEME = "__UI_THEME__";
  const WORKSPACE_ROUTING = __WORKSPACE_ROUTING__;
  const normalizeTheme = (theme) => ["light", "dark", "system"].includes(theme) ? theme : "light";
  const resolveTheme = (theme) => {
    const normalized = normalizeTheme(theme);
    if (normalized !== "system") return normalized;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };
  const applyTheme = (theme, persist = true) => {
    const selected = normalizeTheme(theme);
    const resolved = resolveTheme(selected);
    document.documentElement.dataset.theme = resolved;
    document.documentElement.classList.toggle("dark", resolved === "dark");
    document.documentElement.dataset.themePreference = selected;
    if (persist) localStorage.setItem(THEME_STORAGE_KEY, selected);
    const themeLabel = document.getElementById("app-theme-label");
    if (themeLabel) themeLabel.textContent = resolved === "dark" ? "深色" : "浅色";
    const themeButton = document.getElementById("app-theme-toggle");
    if (themeButton) {
      themeButton.setAttribute("aria-label", resolved === "dark" ? "切换浅色主题" : "切换深色主题");
      themeButton.title = resolved === "dark" ? "切换浅色主题" : "切换深色主题";
    }
    return resolved;
  };
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  applyTheme(storedTheme || CONFIGURED_THEME, false);
  window.addEventListener("message", (event) => {
    if (event.origin === window.location.origin && event.data?.type === "aiquant:theme") {
      applyTheme(event.data.theme, false);
    }
  });
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
      if ((localStorage.getItem(THEME_STORAGE_KEY) || CONFIGURED_THEME) === "system") applyTheme("system", false);
    });
  }
  const isWorkspaceEmbedded = new URLSearchParams(window.location.search).get("embedded") === "1";
  __WORKSPACE_ROUTES__
  document.addEventListener("click", (event) => {
    if (event.target.closest('[role="tab"]')) {
      setTimeout(() => window.dispatchEvent(new Event("resize")), 100);
      setTimeout(() => window.dispatchEvent(new Event("resize")), 360);
    }
  });
  const bindHeaderRefresh = () => {
    const refreshButton = document.getElementById("app-refresh-button");
    if (!refreshButton || refreshButton.dataset.bound === "1") return true;
    refreshButton.dataset.bound = "1";
    const isVisible = (element) => {
      if (!element) return false;
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return false;
      const style = getComputedStyle(element);
      return style.display !== "none" && style.visibility !== "hidden";
    };
    refreshButton.addEventListener("click", () => {
      const candidates = Array.from(document.querySelectorAll("button.page-refresh-btn")).filter(isVisible);
      let target = null;
      let bestDepth = -1;
      candidates.forEach((button) => {
        let depth = 0;
        let panel = button.closest(".tabitem");
        while (panel) {
          depth += 1;
          panel = panel.parentElement ? panel.parentElement.closest(".tabitem") : null;
        }
        if (depth >= bestDepth) {
          bestDepth = depth;
          target = button;
        }
      });
      if (target) {
        refreshButton.classList.add("spinning");
        target.click();
        setTimeout(() => refreshButton.classList.remove("spinning"), 1200);
      } else {
        refreshButton.classList.add("spinning");
        setTimeout(() => window.location.reload(), 250);
      }
    });
    return true;
  };
  if (!bindHeaderRefresh()) {
    const headerObserver = new MutationObserver(() => {
      if (bindHeaderRefresh()) headerObserver.disconnect();
    });
    headerObserver.observe(document.body, { childList: true, subtree: true });
  }
  const normalizeLinks = () => {
    document.querySelectorAll(".data-table a, .dashboard-news-card a, .prose a, .markdown a").forEach((anchor) => {
      anchor.setAttribute("target", "_blank");
      anchor.setAttribute("rel", "noopener noreferrer");
    });
  };
  const colorizeTables = () => {
    document.querySelectorAll(".data-table td").forEach((cell) => {
      const text = (cell.innerText || "").trim();
      const rowText = (cell.closest("tr")?.innerText || "").trim();
      const riskMetric = /回撤|波动|VaR|夏普|索提诺|Calmar|超额收益|亏损|手续费|风险/.test(rowText);
      cell.classList.remove("value-positive", "value-negative", "value-warning", "value-strong", "value-safe");
      if (!text) return;
      const numeric = Number(text.replace(/[%￥,]/g, ""));
      if (!Number.isNaN(numeric) && /%|\+|-/.test(text)) {
        if (numeric > 0) cell.classList.add(riskMetric ? "value-warning" : "value-positive");
        if (numeric < 0) cell.classList.add(riskMetric ? "value-positive" : "value-negative");
        return;
      }
      if (/高风险|异常|失败|错误|降级|停用/.test(text)) {
        cell.classList.add("value-warning");
      } else if (/关注|待配置|可选配置|待启动/.test(text)) {
        cell.classList.add("value-strong");
      } else if (/正常|启用|已成交|可用|已完成/.test(text)) {
        cell.classList.add("value-safe");
      }
    });
    normalizeLinks();
  };
  const tableObserver = new MutationObserver(() => colorizeTables());
  tableObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
  setTimeout(colorizeTables, 600);
  setTimeout(normalizeLinks, 800);
  const findVisibleControl = (selector, text, exact = false) => Array.from(document.querySelectorAll(selector))
    .find((button) => {
      const rect = button.getBoundingClientRect();
      const label = (button.innerText || "").trim();
      return rect.width > 8 && rect.height > 8 && (exact ? label === text : label.startsWith(text));
    });
  const findVisibleTab = (text) => findVisibleControl("#main-navigation [role='tab']", text);
  const findVisibleButton = (text) => findVisibleControl("button", text, true);
  const openAiFactorMining = () => {
    const steps = [
      () => findVisibleTab("AI工作台"),
      () => findVisibleTab("模拟模块"),
      () => findVisibleTab("因子挖掘"),
      () => findVisibleButton("刷新因子挖掘"),
    ];
    let step = 0;
    let attempts = 0;
    const run = () => {
      if (step >= steps.length) return;
      const target = steps[step]();
      if (target) {
        target.click();
        step += 1;
        attempts = 0;
        setTimeout(run, 320);
        return;
      }
      attempts += 1;
      if (attempts <= 24) setTimeout(run, 220);
    };
    run();
  };
  const bindAiWorkbenchEntry = () => {
    const tab = findVisibleTab("AI工作台");
    const aiRoute = document.querySelector("#module-navigation [data-module-key='ai']")?.href || "";
    if (!tab && !aiRoute) return false;
    document.querySelectorAll(".ai-workbench-entry-action").forEach((button) => {
      if (button.dataset.aiBound === "1") return;
      button.dataset.aiBound = "1";
      button.addEventListener("click", () => {
        const target = findVisibleTab("AI工作台");
        if (target) {
          target.click();
          setTimeout(openAiFactorMining, 240);
          setTimeout(() => window.dispatchEvent(new Event("resize")), 180);
        } else if (aiRoute && isWorkspaceEmbedded) {
          window.parent.postMessage({ type: "aiquant:navigate", module: "ai" }, window.location.origin);
        } else if (aiRoute) {
          window.location.assign(aiRoute);
        }
      });
    });
    return true;
  };
  if (!bindAiWorkbenchEntry()) {
    const aiNavObserver = new MutationObserver(() => {
      if (bindAiWorkbenchEntry()) aiNavObserver.disconnect();
    });
    aiNavObserver.observe(document.body, { childList: true, subtree: true });
  }
  const aiActionObserver = new MutationObserver(() => bindAiWorkbenchEntry());
  aiActionObserver.observe(document.body, { childList: true, subtree: true });
  const initializeFloatingChat = () => {
    const fab = document.getElementById("ai-floating-button");
    const panel = document.getElementById("ai-floating-panel");
    if (!fab || !panel) return false;
    if (fab.dataset.dragReady === "1") return true;
    fab.dataset.dragReady = "1";
    const clampOpenPanel = () => {
      if (!panel.classList.contains("ai-panel-open")) return;
      const rect = panel.getBoundingClientRect();
      panel.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8))}px`;
      panel.style.top = `${Math.max(8, Math.min(rect.top, window.innerHeight - rect.height - 8))}px`;
    };
    window.addEventListener("resize", clampOpenPanel);
    new ResizeObserver(clampOpenPanel).observe(panel);
    const button = fab.querySelector("button") || fab;
    const close = document.getElementById("ai-floating-close");
    button.title = "大模型问答";
    button.setAttribute("aria-label", "大模型问答");
    const stored = localStorage.getItem("all-in-one-ai-fab-position");
    if (stored) {
      try {
        const position = JSON.parse(stored);
        fab.style.left = `${Math.min(Math.max(position.x, 8), window.innerWidth - 62)}px`;
        fab.style.top = `${Math.min(Math.max(position.y, 8), window.innerHeight - 62)}px`;
        fab.style.right = "auto";
        fab.style.bottom = "auto";
      } catch (_) {}
    }
    let origin = null;
    let moved = false;
    button.addEventListener("pointerdown", (event) => {
      const rect = fab.getBoundingClientRect();
      origin = { x: event.clientX, y: event.clientY, left: rect.left, top: rect.top };
      moved = false;
      button.setPointerCapture(event.pointerId);
    });
    button.addEventListener("pointermove", (event) => {
      if (!origin) return;
      const dx = event.clientX - origin.x;
      const dy = event.clientY - origin.y;
      if (Math.abs(dx) + Math.abs(dy) > 6) moved = true;
      if (!moved) return;
      const x = Math.min(Math.max(origin.left + dx, 8), window.innerWidth - 62);
      const y = Math.min(Math.max(origin.top + dy, 8), window.innerHeight - 62);
      fab.style.left = `${x}px`;
      fab.style.top = `${y}px`;
      fab.style.right = "auto";
      fab.style.bottom = "auto";
    });
    button.addEventListener("pointerup", () => {
      if (moved) {
        const rect = fab.getBoundingClientRect();
        localStorage.setItem("all-in-one-ai-fab-position", JSON.stringify({ x: rect.left, y: rect.top }));
      }
      origin = null;
    });
    button.addEventListener("click", (event) => {
      event.preventDefault();
      if (moved) { moved = false; return; }
      const rect = fab.getBoundingClientRect();
      panel.classList.add("ai-panel-open");
      fab.classList.add("ai-button-hidden");
      const panelRect = panel.getBoundingClientRect();
      const panelWidth = Math.min(panelRect.width || 460, window.innerWidth - 16);
      const panelHeight = Math.min(panelRect.height || 580, window.innerHeight - 96);
      panel.style.left = `${Math.min(Math.max(rect.right - panelWidth, 8), window.innerWidth - panelWidth - 8)}px`;
      panel.style.top = `${Math.min(Math.max(rect.top - panelHeight, 8), window.innerHeight - panelHeight - 8)}px`;
      panel.style.right = "auto";
      panel.style.bottom = "auto";
      setTimeout(() => panel.querySelector("textarea")?.focus(), 80);
    });
    close?.addEventListener("click", () => {
      panel.classList.remove("ai-panel-open");
      fab.classList.remove("ai-button-hidden");
    });
    return true;
  };
  if (!initializeFloatingChat()) {
    const observer = new MutationObserver(() => {
      if (initializeFloatingChat()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
  // ----- i18n DOM translation + market switching -----
  const I18N_DICT = __I18N_DICT__;
  const I18N_TECHNICAL_TEXTS = __I18N_TECHNICAL_TEXTS__;
  const I18N_STORAGE_KEY = "all-in-one-ui-lang";
  const MARKET_STORAGE_KEY = "all-in-one-ui-market";
  const SKIP_I18N_TAGS = new Set(["SCRIPT", "STYLE", "TEXTAREA", "INPUT", "PRE"]);
  const I18N_ATTRS = ["title", "aria-label", "placeholder"];
  const I18N_MAX_TEXT = 360;
  const LANG_MARKET = { zh: "cn", en: "us" };
  const MARKET_LANG = { cn: "zh", us: "en" };
  const I18N_REVERSE = {};
  Object.entries(I18N_DICT).forEach(([source, target]) => {
    if (!I18N_REVERSE[target]) I18N_REVERSE[target] = source;
  });
  const TECH_EN_TO_ZH = {};
  const TECH_ZH_TO_EN = {};
  Object.values(I18N_TECHNICAL_TEXTS).forEach((labels) => {
    if (labels && labels.en && labels.zh) {
      TECH_EN_TO_ZH[labels.en] = labels.zh;
      TECH_ZH_TO_EN[labels.zh] = labels.en;
    }
  });
  const I18N_ENTRIES = Object.entries(I18N_DICT).sort((left, right) => right[0].length - left[0].length);
  const I18N_REVERSE_ENTRIES = Object.entries(I18N_REVERSE).sort((left, right) => right[0].length - left[0].length);
  const i18nTextSources = new WeakMap();
  const i18nInputSources = new WeakMap();
  let uiLang = "zh";
  let i18nTimer = 0;
  let i18nApplying = false;
  const normalizeLang = (lang) => (lang === "en" ? "en" : "zh");
  const normalizeMarketValue = (market) => {
    const value = String(market || "").trim().toLowerCase();
    return value === "us" || value === "usa" || value === "美股" || value.includes("u.s") ? "us" : "cn";
  };
  const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const hasChinese = (value) => /[㐀-鿿]/.test(value);
  const shouldSkipElement = (element, attributes = false) => {
    if (!element) return true;
    if (SKIP_I18N_TAGS.has(element.tagName) && !(attributes && ["INPUT", "TEXTAREA"].includes(element.tagName))) return true;
    return Boolean(element.closest("pre, .no-i18n, .cm-editor, .monaco-editor"));
  };
  const isTranslatableText = (text) => {
    if (!text || text.length > I18N_MAX_TEXT) return false;
    if (/^[-+,.:%\s\d￥$()（）/]+$/.test(text)) return false;
    if (/https?:\/\/|[A-Za-z]:\\|[/\\][\w.-]+\.(py|md|yaml|yml|json|toml|csv|txt)\b/.test(text)) return false;
    return true;
  };
  const exactTechnical = (text, lang) => {
    const labels = I18N_TECHNICAL_TEXTS[text];
    if (labels && labels[lang]) return labels[lang];
    if (lang === "zh" && TECH_EN_TO_ZH[text]) return TECH_EN_TO_ZH[text];
    if (lang === "en" && TECH_ZH_TO_EN[text]) return TECH_ZH_TO_EN[text];
    return "";
  };
  const replaceKnownPhrases = (text, lang) => {
    const entries = lang === "en" ? I18N_ENTRIES : I18N_REVERSE_ENTRIES;
    let translated = text;
    for (const [source, target] of entries) {
      if (source.length < 2 || !translated.includes(source)) continue;
      translated = translated.split(source).join(target);
    }
    return translated;
  };
  const translateForLang = (source, lang) => {
    const normalized = normalizeText(source);
    if (!isTranslatableText(normalized)) return normalized;
    const technical = exactTechnical(normalized, lang);
    if (technical) return technical;
    if (lang === "en") {
      if (I18N_DICT[normalized]) return I18N_DICT[normalized];
      return hasChinese(normalized) ? replaceKnownPhrases(normalized, "en") : normalized;
    }
    if (hasChinese(normalized)) return normalized;
    if (I18N_REVERSE[normalized]) return I18N_REVERSE[normalized];
    return replaceKnownPhrases(normalized, "zh");
  };
  const replaceNodeText = (node, translated) => {
    const current = node.nodeValue || "";
    const raw = current.trim();
    if (!raw || raw === translated) return;
    node.nodeValue = current.replace(raw, translated);
  };
  const translateTextNode = (node) => {
    const parent = node.parentElement;
    if (!parent) return;
    if (shouldSkipElement(parent)) return;
    const raw = (node.nodeValue || "").trim();
    if (!isTranslatableText(raw)) return;
    const previous = i18nTextSources.get(node);
    const source = previous && (raw === previous.source || raw === previous.rendered) ? previous.source : raw;
    const translated = translateForLang(source, uiLang);
    if (translated !== raw) {
      i18nTextSources.set(node, { source, rendered: translated });
      replaceNodeText(node, translated);
    }
  };
  const attrDatasetKey = (attr) => `i18n${attr.replace(/(^|-)(\w)/g, (_, __, char) => char.toUpperCase())}Src`;
  const translateElementAttributes = (element) => {
    if (shouldSkipElement(element, true)) return;
    // Gradio keeps the actual selected value in its component store. Translate
    // only an unfocused listbox's display, and restore it before user editing.
    const listbox = element.tagName === "INPUT" && element.getAttribute("role") === "listbox";
    const readonlyLabel = ["INPUT", "TEXTAREA"].includes(element.tagName) && (element.readOnly || element.disabled) &&
      (I18N_DICT[normalizeText(element.value)] || i18nInputSources.has(element));
    if ((listbox || readonlyLabel) && element !== document.activeElement) {
      const raw = element.value;
      const previous = i18nInputSources.get(element);
      const source = previous && (raw === previous.source || raw === previous.rendered) ? previous.source : raw;
      const rendered = translateForLang(source, uiLang);
      if (rendered !== raw) {
        i18nInputSources.set(element, { source, rendered });
        element.value = rendered;
      }
    }
    I18N_ATTRS.forEach((attr) => {
      const raw = (element.getAttribute(attr) || "").trim();
      if (!isTranslatableText(raw)) return;
      const key = attrDatasetKey(attr);
      const previousSource = element.dataset[key];
      const source = previousSource && (raw === previousSource || raw === element.dataset[`${key}Rendered`]) ? previousSource : raw;
      const translated = translateForLang(source, uiLang);
      if (translated !== raw) {
        element.dataset[key] = source;
        element.dataset[`${key}Rendered`] = translated;
        element.setAttribute(attr, translated);
      }
    });
  };
  const translateDocument = (root) => {
    const scope = root && root.querySelectorAll ? root : document.body;
    if (!scope || i18nApplying) return;
    i18nApplying = true;
    try {
      const elements = scope === document.body ? Array.from(scope.querySelectorAll("*")) : [scope, ...Array.from(scope.querySelectorAll("*"))];
      elements.forEach((element) => translateElementAttributes(element));
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      let node = walker.nextNode();
      while (node) { translateTextNode(node); node = walker.nextNode(); }
    } finally {
      i18nApplying = false;
    }
  };
  const scheduleTranslate = () => {
    clearTimeout(i18nTimer);
    i18nTimer = setTimeout(() => translateDocument(), 220);
  };
  document.addEventListener("focusin", (event) => {
    const previous = i18nInputSources.get(event.target);
    if (previous && event.target.value === previous.rendered) event.target.value = previous.source;
  });
  document.addEventListener("focusout", scheduleTranslate);
  const i18nObserver = new MutationObserver((mutations) => {
    if (i18nApplying) return;
    for (const mutation of mutations) {
      if (mutation.addedNodes.length > 0 || mutation.type === "characterData") { scheduleTranslate(); return; }
    }
  });
  i18nObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
  const updateMarketButtons = (market) => {
    const cn = document.getElementById("app-market-cn");
    const us = document.getElementById("app-market-us");
    if (cn) cn.classList.toggle("active", market === "cn");
    if (us) us.classList.toggle("active", market === "us");
  };
  const findMarketRadio = (market) => {
    const label = market === "us" ? "美股" : "A股";
    return document.querySelector(`#market-switcher input[type="radio"][value="${label}"]`);
  };
  const applyMarketSelection = (market, options = {}) => {
    const normalizedMarket = normalizeMarketValue(market);
    localStorage.setItem(MARKET_STORAGE_KEY, normalizedMarket);
    updateMarketButtons(normalizedMarket);
    if (options.syncLanguage) {
      const targetLang = MARKET_LANG[normalizedMarket] || "zh";
      if (targetLang !== uiLang) applyLanguage(targetLang, { syncMarket: false });
    }
    const radio = findMarketRadio(normalizedMarket);
    if (radio && !radio.checked) radio.click();
  };
  const applyLanguage = (lang, options = {}) => {
    const normalizedLang = normalizeLang(lang);
    uiLang = normalizedLang;
    localStorage.setItem(I18N_STORAGE_KEY, normalizedLang);
    document.documentElement.setAttribute("data-ui-lang", normalizedLang);
    const label = document.getElementById("app-language-label");
    if (label) label.textContent = normalizedLang === "en" ? "EN / ZH" : "中 / EN";
    translateDocument();
    if (options.syncMarket) applyMarketSelection(LANG_MARKET[normalizedLang], { syncLanguage: false });
  };
  const bindHeaderToggles = () => {
    const langButton = document.getElementById("app-language-toggle");
    const cnButton = document.getElementById("app-market-cn");
    const usButton = document.getElementById("app-market-us");
    if (!langButton || !cnButton || !usButton) return false;
    if (langButton.dataset.i18nBound !== "1") {
      langButton.dataset.i18nBound = "1";
      langButton.addEventListener("click", () => applyLanguage(uiLang === "en" ? "zh" : "en", { syncMarket: true }));
    }
    if (cnButton.dataset.marketBound !== "1") {
      cnButton.dataset.marketBound = "1";
      cnButton.addEventListener("click", () => applyMarketSelection("cn", { syncLanguage: true }));
    }
    if (usButton.dataset.marketBound !== "1") {
      usButton.dataset.marketBound = "1";
      usButton.addEventListener("click", () => applyMarketSelection("us", { syncLanguage: true }));
    }
    return true;
  };
  if (!bindHeaderToggles()) {
    const toggleObserver = new MutationObserver(() => {
      if (bindHeaderToggles()) toggleObserver.disconnect();
    });
    toggleObserver.observe(document.body, { childList: true, subtree: true });
  }
  const storedMarket = normalizeMarketValue(localStorage.getItem(MARKET_STORAGE_KEY) || "cn");
  const storedLangValue = localStorage.getItem(I18N_STORAGE_KEY);
  const storedLang = storedLangValue ? normalizeLang(storedLangValue) : MARKET_LANG[storedMarket];
  setTimeout(() => applyLanguage(storedLang, { syncMarket: true }), 300);
  setTimeout(() => applyLanguage(storedLang, { syncMarket: true }), 1000);
  setTimeout(() => applyLanguage(storedLang, { syncMarket: true }), 2400);
}
