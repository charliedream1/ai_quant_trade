// Shared child routing for embedded and standalone Gradio modules. No polling.
(() => {
  const config = WORKSPACE_ROUTING;
  const module = location.pathname.match(/\/app\/([^/]+)/)?.[1];
  const views = config.modules[module] || {};
  if (!Object.keys(views).length) return;
  let epoch = 0;
  let currentView = "", currentNonce = "";
  let currentTab = "";
  let preparedMarket = "";
  let securityValue, securityPending = false, securitySerial = 0;
  let securityRequest = null;
  const viewKey = () => currentTab ? currentView + "/" + currentTab : currentView;
  const validContext = (name, value) => config.context_values[name] ? config.context_values[name].includes(value)
    : new RegExp(config.context_patterns?.[name] || "^[0-9]+$").test(String(value || ""));
  const tabButtons = (group) => Array.from(document.querySelectorAll(`#${group.id} [role="tab"][data-tab-id]`));
  const showResearch = (group) => {
    const page = document.getElementById(`market-${currentView}-view`);
    if (!page) return false;
    document.querySelectorAll("#market-research-views .research-page").forEach((item) => {
      item.toggleAttribute("data-research-visible", item === page);
    });
    const nativeStrip = document.querySelector(`#${group.id}-panels > .tab-wrapper`);
    const nativeButton = nativeStrip?.querySelector(`[data-tab-id="${currentTab}"]`);
    if (!nativeButton) return false;
    nativeStrip.inert = true;
    if (nativeButton.getAttribute("aria-selected") !== "true") nativeButton.click();
    const panel = document.getElementById(`research-panel-${currentTab}`);
    const action = group.tabs[currentTab]?.action;
    if (!panel || (action && !document.getElementById(action))) return false;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", `research-tab-${currentTab}`);
    tabButtons(group).forEach((button) => {
      const selected = button.dataset.tabId === currentTab;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
      if (selected && button.offsetParent !== null) {
        const strip = button.closest(".research-tab-strip");
        const box = button.getBoundingClientRect(), bounds = strip.getBoundingClientRect();
        if (box.left < bounds.left) strip.scrollLeft -= bounds.left - box.left;
        if (box.right > bounds.right) strip.scrollLeft += box.right - bounds.right;
      }
    });
    updateActions();
    document.dispatchEvent(new Event("aiquant:research-page-shown"));
    return true;
  };
  const setTextInput = (input, value) => {
    if (input.value === String(value)) return;
    input.value = String(value);
    input.dispatchEvent(new Event("input", {bubbles: true}));
    input.dispatchEvent(new Event("change", {bubbles: true}));
  };
  const reportHeader = () => document.querySelector("#page-skill-panel > .label-wrap");
  const closeReport = () => {
    const header = reportHeader();
    if (header?.classList.contains("open")) header.click();
  };
  const reportSupported = () => config.report_views.includes(`${module}/${viewKey()}`);
  const setReportField = (id, value) => {
    const field = document.querySelector(`#${id} textarea, #${id} input`);
    if (!field) return false;
    if (field.value !== value) {
      field.value = value;
      field.dispatchEvent(new Event("input", {bubbles: true}));
      field.dispatchEvent(new Event("change", {bubbles: true}));
    }
    return true;
  };
  const setReportLanguage = () => setReportField("page-skill-language", document.documentElement.dataset.uiLang || "zh");
  const openReport = () => {
    const view = viewKey();
    if (!reportSupported()) return;
    waitFor(() => {
      const header = reportHeader();
      const trigger = document.getElementById("page-skill-open");
      if (!header || !trigger || !setReportField("page-skill-view", view) || !setReportLanguage()) return false;
      queueMicrotask(() => {
        if (view !== viewKey() || !header.isConnected || window.aiquantPageWork?.active === false) return;
        const group = config.tab_groups[`${module}/${currentView}`];
        const tabs = group && document.querySelector(`#${group.id} .research-tab-strip`);
        if (tabs) {
          const height = Math.max(0, tabs.getBoundingClientRect().bottom);
          header.parentElement.style.setProperty("--research-tab-bottom", `${Math.ceil(height) + 8}px`);
        }
        if (!header.classList.contains("open")) header.click();
        document.getElementById("page-skill-open")?.click();
      });
      return true;
    }, epoch);
  };
  const updateActions = () => {
    const group = config.tab_groups[`${module}/${currentView}`];
    setReportField("page-skill-view", viewKey());
    const standalone = document.getElementById("page-skill-standalone");
    if (standalone) standalone.hidden = Boolean(group) || !reportSupported();
    const actions = document.querySelector("#research-workspace-actions .research-actions");
    if (!actions || !group) return;
    actions.closest("#research-workspace-actions")?.toggleAttribute(
      "data-security-pending", currentView === "stock" && securityPending,
    );
    const refresh = actions.querySelector("[data-research-refresh]");
    const ai = actions.querySelector(".page-report-action");
    refresh.dataset.researchRefresh = group.tabs[currentTab]?.action || "";
    refresh.hidden = !document.getElementById(refresh.dataset.researchRefresh);
    ai.dataset.reportView = currentTab === "relationships" ? "relations" : "";
    ai.hidden = !ai.dataset.reportView && !reportSupported();
    actions.hidden = refresh.hidden && ai.hidden;
  };
  const markSecurity = (value) => {
    const page = document.getElementById("market-stock-view");
    const actions = document.getElementById("research-workspace-actions");
    page?.toggleAttribute("data-security-pending", true);
    actions?.toggleAttribute("data-security-pending", true);
    const initial = document.getElementById("stock-security-initial");
    if (initial) initial.textContent = "";
    const status = document.getElementById("stock-security-pending-message");
    if (status) status.textContent = [value.trim(), window.aiquantTranslate?.("正在切换标的…") || "正在切换标的…"]
      .filter(Boolean).join(" · ");
  };
  const resetSecurity = () => {
    if (currentView !== "stock" || !securityPending) return;
    const scope = window.aiquantPageWork?.state.revision;
    if (securityRequest?.scope === scope && securityRequest?.value === securityValue) return;
    const token = String(++securitySerial);
    const retry = document.getElementById("stock-security-retry");
    if (retry) retry.hidden = true;
    if (!setReportField("stock-security-revision", token)) return;
    const button = document.querySelector("button#stock-security-reset, #stock-security-reset button");
    if (!button) return;
    securityRequest = {scope, value: securityValue};
    const ticket = epoch;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (ticket === epoch && token === String(securitySerial)) button.click();
    }));
    setTimeout(() => {
      if (retry && token === String(securitySerial) && securityPending) {
        securityRequest = null;
        retry.hidden = false;
      }
    }, config.route_wait_ms);
    waitFor(() => {
      if (token !== String(securitySerial)) return true;
      if (document.querySelector("#stock-security-ack [data-stock-revision]")?.dataset.stockRevision !== token) return false;
      securityPending = false;
      securityRequest = null;
      document.getElementById("market-stock-view")?.removeAttribute("data-security-pending");
      document.getElementById("research-workspace-actions")?.removeAttribute("data-security-pending");
      return true;
    }, epoch);
  };
  const commitSecurity = (value, advance = false) => {
    if (securityValue === undefined && !advance) {
      securityValue = value;
      const initial = document.getElementById("stock-security-initial");
      if (initial) initial.textContent = value;
      return;
    }
    if (value === securityValue && !securityPending) return;
    if (value !== securityValue) securityRequest = null;
    securityValue = value;
    securityPending = true;
    markSecurity(value);
    resetContext();
    if (advance) {
      if (isWorkspaceEmbedded) parent.aiquantSelectSubview?.(currentTab, true);
      else {
        const work = window.aiquantPageWork;
        const scope = work?.state;
        if (scope) { work.deactivate(); work.activate({...scope, revision: scope.revision + 1}); }
      }
    }
    resetSecurity();
  };
  const resetContext = () => {
    closeReport();
    const badge = document.querySelector("#assistant-context-scope .prose");
    const state = document.getElementById("assistant-context-state");
    if (badge && state) badge.textContent = state.dataset.reset;
  };
  const standaloneScope = () => {
    const work = window.aiquantPageWork;
    if (!work || work.state.view === viewKey() && work.active) return;
    const scope = work.state;
    work.deactivate();
    work.activate({...scope, revision: scope.revision + 1, view: viewKey()});
  };
  const cleanups = new Set(), applied = new Map();
  const cancel = () => {
    epoch += 1;
    cleanups.forEach((cleanup) => cleanup());
    cleanups.clear();
  };
  const waitFor = (action, ticket) => {
    if (ticket !== epoch || action()) return;
    const observer = new MutationObserver(() => {
      if (ticket !== epoch || action()) cleanup();
    });
    const cleanup = () => { observer.disconnect(); clearTimeout(timer); cleanups.delete(cleanup); };
    const timer = setTimeout(cleanup, config.route_wait_ms);
    cleanups.add(cleanup);
    observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ["class", "style"]});
  };
  const apply = (data) => {
    const alias = config.aliases.find((row) => row.module === data.module && row.view === data.view);
    if (alias && alias.target === module) data = {...data, view: alias.target_view, tab: alias.tab || data.tab};
    if (data.module !== module || !views[data.view]) return;
    const key = `${module}/${data.view}`, group = config.tab_groups[key];
    const requested = group?.aliases?.[data.tab] || data.tab;
    const section = group ? (Object.hasOwn(group.tabs, requested) ? requested : group.default) : "";
    if (currentView === data.view && currentNonce === String(data.target_nonce || `standalone:${location.search}`)) {
      if (data.openReport) openReport();
      return;
    }
    cancel();
    const ticket = epoch;
    const nonce = String(data.target_nonce || `standalone:${location.search}`);
    const contextViewChanged = currentView !== data.view || currentTab !== section;
    currentView = data.view;
    currentTab = section;
    if (contextViewChanged) resetContext();
    if (!isWorkspaceEmbedded && group) standaloneScope();
    updateActions();
    currentNonce = nonce;
    waitFor(() => {
      const tab = Array.from(document.querySelectorAll(".module-tabs > .tab-wrapper button"))
        .find((button) => !button.closest(".visually-hidden") &&
          (group ? button.dataset.tabId === data.view
            : (window.aiquantUiSource?.(button) || button.textContent.trim()) === views[data.view]));
      if (group) {
        if (!showResearch(group)) return false;
      } else {
        if (!tab) return false;
        if (tab.getAttribute("aria-selected") !== "true") tab.click();
      }
      if (!group && config.tabs.includes(data.tab)) {
        waitFor(() => {
          const nested = Array.from(document.querySelectorAll('[role="tab"]'))
            .find((item) => item.offsetParent !== null && (window.aiquantUiSource?.(item) || item.textContent.trim()) === data.tab);
          if (!nested) return false;
          if (nested.getAttribute("aria-selected") !== "true") nested.click();
          return true;
        }, ticket);
      }
      const pending = new Map(Object.entries(data.context || {}).filter(([name,value]) =>
        (config.context_targets[key] || []).includes(name) &&
        validContext(name, value)));
      waitFor(() => {
        pending.forEach((value, name) => {
          const identity = `${key}/${name}`;
          if (applied.get(identity) === nonce) { pending.delete(name); return; }
          if (name === "graph_mode" && section !== "relationships") { pending.delete(name); return; }
          const input = name === "graph_mode"
            ? document.querySelector(`#relation-graph-mode input[value="${value}"]`)
            : document.querySelector(`#${config.context_fields[name]} input, #${config.context_fields[name]} textarea`);
          if (!input) return;
          pending.delete(name);
          applied.set(identity, nonce);
          if (name === "graph_mode") {
            if (!input.checked) input.click();
          } else {
            setTextInput(input, value);
            if (name === "symbol") commitSecurity(input.value);
          }
          if (name === "task_id") requestAnimationFrame(() => requestAnimationFrame(() => {
            if (ticket === epoch) document.getElementById("route-backtest-open")?.click();
          }));
        });
        return pending.size === 0;
      }, ticket);
      if (key === "market/stock") {
        const market = (data.page_scope?.market || new URLSearchParams(location.search).get("market")
          || localStorage.getItem("all-in-one-ui-market") || "cn").toUpperCase();
        waitFor(() => {
          const field = document.querySelector("#fundamentals-symbol textarea, #fundamentals-symbol input");
          if (!field) return false;
          const requestedSymbol = data.context?.symbol;
          if (market !== preparedMarket && !validContext("symbol", requestedSymbol)) {
            setTextInput(field, config.stock_defaults[market] || "");
          }
          preparedMarket = market;
          if (securityValue === undefined || securityPending) commitSecurity(field.value);
          return true;
        }, ticket);
      }
      if (key === config.pipeline_target && /^[0-9]+$/.test(String(data.pipeline_version || ""))) {
        waitFor(() => {
          if (applied.get(key + "/version") === nonce) return true;
          const input = document.querySelector("#pipeline-route-version textarea, #pipeline-route-version input");
          if (!input) return false;
          applied.set(key + "/version", nonce);
          input.value = String(data.pipeline_version);
          input.dispatchEvent(new Event("input", {bubbles: true}));
          return true;
        }, ticket);
      }
      const id = data.view === "workshop" ? "workspace-activate-composition" : "";
      if (id) waitFor(() => {
        const button = document.getElementById(id);
        if (!button) return false;
        if (!button.classList.contains("hidden")) button.click();
        return true;
      }, ticket);
      return true;
    }, ticket);
    if (data.openReport) openReport();
  };
  const fromUrl = () => {
    const query = new URLSearchParams(location.search);
    apply({module, view: query.get("view") || Object.keys(views)[0], tab: query.get("tab"),
      context: Object.fromEntries(Object.keys(config.context_fields).map((name) => [name,query.get(name)])),
      pipeline_version: query.get("pipeline_version")});
  };
  if (isWorkspaceEmbedded) {
    document.documentElement.classList.add("gradio-embedded");
    window.addEventListener("message", (event) => {
      if (event.origin !== location.origin || event.source !== window.parent) return;
      const work = window.aiquantPageWork;
      const revision = work?.state.revision;
      if (event.data?.type === "aiquant:select-view" &&
          (!revision || !event.data.page_scope || event.data.page_scope.revision >= revision)) apply(event.data);
      if (event.data?.type === "aiquant:deactivate" &&
          (!revision || !event.data.revision || event.data.revision === revision)) {
        closeReport();
        cancel();
      }
    });
    window.parent.postMessage({type: "aiquant:ready"}, location.origin);
    document.addEventListener("click", (event) => {
      const link = event.target.closest("#module-navigation [data-module-key], a[href^='/app/?module=']");
      if (!link) return;
      event.preventDefault();
      const url = new URL(link.href, location.origin), query = url.searchParams;
      window.parent.postMessage({type: "aiquant:navigate", module: link.dataset.moduleKey || query.get("module"),
        view: query.get("view"), tab: query.get("tab"), market: query.get("market"), pipeline_version: query.get("pipeline_version"),
        context: Object.fromEntries(Object.keys(config.context_fields).map((name) => [name,query.get(name)]))}, location.origin);
    });
  } else {
    fromUrl();
    window.addEventListener("popstate", fromUrl);
  }
  document.addEventListener("click", (event) => {
    if (currentView === "stock" && securityPending && event.target.closest("#research-workspace-actions")) return;
    if (event.target.closest("#stock-security-retry")) {
      const field = document.querySelector("#fundamentals-symbol textarea, #fundamentals-symbol input");
      if (field) commitSecurity(field.value, true);
      return;
    }
    const refresh = event.target.closest("[data-research-refresh]");
    if (refresh) {
      document.querySelector(`#${refresh.dataset.researchRefresh} button, button#${refresh.dataset.researchRefresh}`)?.click();
      return;
    }
    const button = event.target.closest("#page-skill-standalone, .page-report-action");
    if (!button) return;
    if (button.dataset.reportView === "relations") {
      document.querySelector('#relation-graph-mode input[type="radio"][value="model"]')?.click();
    } else openReport();
  });
  window.addEventListener("aiquant:language-changed", setReportLanguage);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeReport();
  });
  document.addEventListener("input", (event) => {
    if (!event.isTrusted || !event.target.matches("input, textarea")) return;
    if (currentView === "stock" && event.target.closest("#fundamentals-symbol") && event.target.value !== securityValue) {
      securityPending = true;
      securitySerial += 1;
      markSecurity(event.target.value);
      resetContext();
    }
    const key = `${module}/${currentView}`;
    const name = (config.context_targets[key] || []).find((name) => event.target.closest(`#${config.context_fields[name]}`));
    if (!name) return;
    const value = event.target.value;
    if (value && !validContext(name, value)) return;
    applied.set(`${key}/${name}`, currentNonce);
    if (isWorkspaceEmbedded) window.parent.postMessage({type: "aiquant:context-edited", module, view: currentView, name, value}, location.origin);
    else {
      const url = new URL(location.href);
      if (value) url.searchParams.set(name, value); else url.searchParams.delete(name);
      history.replaceState({}, "", url);
    }
  });
  const selectTab = (button) => {
    const group = config.tab_groups[`${module}/${currentView}`];
    if (!group || !button) return;
    if (!tabButtons(group).includes(button)) return;
    const next = button.dataset.tabId;
    if (!Object.hasOwn(group.tabs, next) || next === currentTab) return;
    currentTab = next;
    cancel();
    resetContext();
    if (isWorkspaceEmbedded) parent.aiquantSelectSubview?.(next);
    else {
      standaloneScope();
      const url = new URL(location.href);
      url.searchParams.set("view", currentView);
      url.searchParams.set("tab", next);
      history.pushState({}, "", url);
    }
    waitFor(() => showResearch(group), epoch);
    if (securityPending) {
      const field = document.querySelector("#fundamentals-symbol textarea, #fundamentals-symbol input");
      if (field) commitSecurity(field.value);
    }
  };
  document.addEventListener("click", (event) => {
    if (event.isTrusted) selectTab(event.target.closest?.("[role='tab']"));
  }, true);
  document.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const group = config.tab_groups[`${module}/${currentView}`];
    if (!group) return;
    const buttons = tabButtons(group);
    const index = buttons.indexOf(event.target);
    if (index === -1) return;
    event.preventDefault();
    const offset = event.key === "ArrowLeft" ? -1 : 1;
    const next = buttons[event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1
      : (index + offset + buttons.length) % buttons.length];
    selectTab(next);
    next.focus({preventScroll: true});
  }, true);
  document.addEventListener("change", (event) => {
    if (!event.isTrusted || currentView !== "stock" || !event.target.closest?.("#fundamentals-symbol")) return;
    commitSecurity(event.target.value, true);
  }, true);
  // Keep the shell's independent-window target aligned with genuine in-page tab clicks.
  document.addEventListener("click", (event) => {
    if (!event.isTrusted) return;
    const button = event.target.closest(".module-tabs > .tab-wrapper button");
    const view = Object.hasOwn(views, button?.dataset.tabId) ? button.dataset.tabId
      : Object.keys(views).find((key) => views[key] === (window.aiquantUiSource?.(button) || button?.textContent.trim()));
    if (!view || view === currentView) return;
    if (isWorkspaceEmbedded) {
      const scope = parent.aiquantSelectView?.(module, view);
      if (scope) window.aiquantPageWork?.activate(scope);
    } else {
      window.aiquantPageWork?.deactivate();
      window.aiquantPageWork?.activate();
    }
    closeReport();
    currentView = view;
    setReportField("page-skill-view", view);
    const standalone = document.getElementById("page-skill-standalone");
    if (standalone) standalone.hidden = !config.report_views.includes(`${module}/${view}`);
    cancel();
    if (isWorkspaceEmbedded) window.parent.postMessage({type: "aiquant:view-selected", module, view}, location.origin);
    else {
      const url = new URL(location.href), key = `${module}/${view}`;
      url.searchParams.set("view", view);
      url.searchParams.delete("tab");
      if (key !== config.pipeline_target) url.searchParams.delete("pipeline_version");
      Object.keys(config.context_fields).forEach((name) => {
        if (!(config.context_targets[key] || []).includes(name)) url.searchParams.delete(name);
      });
      history.pushState({}, "", url);
    }
  }, true);
  if (!isWorkspaceEmbedded && module === "market") requestAnimationFrame(fromUrl);
})();
