// Shared child routing for embedded and standalone Gradio modules. No polling.
(() => {
  const config = WORKSPACE_ROUTING;
  const module = location.pathname.match(/\/app\/([^/]+)/)?.[1];
  const views = config.modules[module] || {};
  if (!Object.keys(views).length) return;
  let epoch = 0;
  let currentView = "", currentNonce = "";
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
    cancel();
    const ticket = epoch, key = `${module}/${data.view}`;
    const nonce = String(data.target_nonce || `standalone:${location.search}`);
    currentView = data.view;
    currentNonce = nonce;
    waitFor(() => {
      const tab = Array.from(document.querySelectorAll(".module-tabs > .tab-wrapper button"))
        .find((button) => !button.closest(".visually-hidden") && (window.aiquantUiSource?.(button) || button.textContent.trim()) === views[data.view]);
      if (!tab) return false;
      tab.click();
      if (config.tabs.includes(data.tab)) {
        waitFor(() => {
          const nested = Array.from(document.querySelectorAll('[role="tab"]'))
            .find((item) => item.offsetParent !== null && (window.aiquantUiSource?.(item) || item.textContent.trim()) === data.tab);
          if (!nested) return false;
          nested.click();
          return true;
        }, ticket);
      }
      const pending = new Map(Object.entries(data.context || {}).filter(([name,value]) =>
        (config.context_targets[key] || []).includes(name) &&
        (config.context_values[name] ? config.context_values[name].includes(value) : /^[0-9]+$/.test(String(value)))));
      waitFor(() => {
        pending.forEach((value, name) => {
          const identity = `${key}/${name}`;
          if (applied.get(identity) === nonce) { pending.delete(name); return; }
          const input = document.querySelector(`#${config.context_fields[name]} input, #${config.context_fields[name]} textarea`);
          if (!input) return;
          pending.delete(name);
          applied.set(identity, nonce);
          input.value = String(value);
          input.dispatchEvent(new Event("input", {bubbles: true}));
          input.dispatchEvent(new Event("change", {bubbles: true}));
          if (name === "task_id") requestAnimationFrame(() => requestAnimationFrame(() => {
            if (ticket === epoch) document.getElementById("route-backtest-open")?.click();
          }));
        });
        return pending.size === 0;
      }, ticket);
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
      const id = {workshop: "workspace-activate-composition", resources: "workspace-activate-pool-pipeline"}[data.view];
      if (id) waitFor(() => {
        const button = document.getElementById(id);
        if (!button) return false;
        if (!button.classList.contains("hidden")) button.click();
        return true;
      }, ticket);
      return true;
    }, ticket);
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
      if (event.data?.type === "aiquant:select-view") apply(event.data);
      if (event.data?.type === "aiquant:deactivate") cancel();
    });
    window.parent.postMessage({type: "aiquant:ready"}, location.origin);
    document.addEventListener("click", (event) => {
      const link = event.target.closest("#module-navigation [data-module-key], a[href^='/app/?module=']");
      if (!link) return;
      event.preventDefault();
      const url = new URL(link.href, location.origin), query = url.searchParams;
      window.parent.postMessage({type: "aiquant:navigate", module: link.dataset.moduleKey || query.get("module"),
        view: query.get("view"), tab: query.get("tab"), pipeline_version: query.get("pipeline_version"),
        context: Object.fromEntries(Object.keys(config.context_fields).map((name) => [name,query.get(name)]))}, location.origin);
    });
  } else {
    fromUrl();
    window.addEventListener("popstate", fromUrl);
  }
  document.addEventListener("input", (event) => {
    if (!event.isTrusted || !event.target.matches("input, textarea")) return;
    const key = `${module}/${currentView}`;
    const name = (config.context_targets[key] || []).find((name) => event.target.closest(`#${config.context_fields[name]}`));
    if (!name) return;
    const value = event.target.value;
    if (value && !(config.context_values[name] ? config.context_values[name].includes(value) : /^[0-9]+$/.test(value))) return;
    applied.set(`${key}/${name}`, currentNonce);
    if (isWorkspaceEmbedded) window.parent.postMessage({type: "aiquant:context-edited", module, view: currentView, name, value}, location.origin);
    else {
      const url = new URL(location.href);
      if (value) url.searchParams.set(name, value); else url.searchParams.delete(name);
      history.replaceState({}, "", url);
    }
  });
  // Keep the shell's independent-window target aligned with genuine in-page tab clicks.
  document.addEventListener("click", (event) => {
    if (!event.isTrusted) return;
    const button = event.target.closest(".module-tabs > .tab-wrapper button");
    const view = Object.keys(views).find((key) => views[key] === (window.aiquantUiSource?.(button) || button?.textContent.trim()));
    if (!view) return;
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
  });
})();
