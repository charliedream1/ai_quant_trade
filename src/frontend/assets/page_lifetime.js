// Runs before Gradio hydrates so captured fetch references carry page ownership.
(() => {
  const preview = /\/file-previews\/[a-f0-9]{32}\/view$/.test(location.pathname);
  if (window.aiquantPageWork || (!preview && !/\/app\/[^/]+\/?$/.test(location.pathname))) return;
  const nativeFetch = window.fetch.bind(window);
  const NativeEventSource = window.EventSource;
  const query = new URLSearchParams(location.search);
  const prefix = document.currentScript.src.replace(/\/workspace\/lifetime\.js.*$/, "");
  const embedded = query.get("embedded") === "1" || (preview && parent !== window);
  const randomOwner = () => crypto.randomUUID().replaceAll("-", "");
  const parentScope = () => {
    try { return embedded && parent.aiquantWorkspaceLifetime; } catch { return null; }
  };
  let state = preview ? {owner: randomOwner(), revision: 1, view: "preview"} : query.get("page_owner")
    ? {owner: query.get("page_owner"), revision: Number(query.get("page_revision")) || 1, view: query.get("view")}
    : parentScope() || {owner: randomOwner(), revision: 1};
  let active = true;
  const controllers = new Map(), streams = new Set(), queued = new Map();
  const cancelledViews = new Set();
  const banner = () => {
    if (!document.body) return;
    let element = document.getElementById("page-work-cancelled");
    if (!element) {
      element = document.createElement("p"); element.id = "page-work-cancelled";
      element.setAttribute("role", "status"); element.className = "no-i18n";
      element.textContent = __CANCELLED_MESSAGE__;
      element.style.cssText = "padding:10px 16px;margin:8px;border:1px solid #d5a500;border-radius:6px;font:14px sans-serif";
      document.body.prepend(element);
    }
    element.hidden = !active || !cancelledViews.has(state.view);
  };
  const signal = (action, value = state) => nativeFetch(prefix + "/workspace/lifetime", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({owner: value.owner, revision: value.revision, action,
      module: location.pathname.match(/\/app\/([^/]+)/)?.[1] || "preview", view: value.view || "unknown"}), keepalive: true,
  }).catch(() => {});
  const abort = () => {
    queued.forEach((item) => nativeFetch(item.url, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(item.body),
    }).catch(() => {}));
    queued.clear();
    controllers.forEach((url, controller) => {
      // Let Gradio deliver its normal close_stream after /cancel. Abrupt SSE disconnects
      // trigger an upstream async-generator error on some supported Gradio releases.
      if (!url.pathname.endsWith("/queue/data")) { controller.abort(); controllers.delete(controller); }
    });
    streams.forEach((stream) => { if (!stream.url.includes("/queue/data")) stream.close(); });
  };
  const deactivate = () => {
    if (!active) return;
    if (controllers.size || queued.size) cancelledViews.add(state.view);
    active = false;
    abort();
    signal("deactivate");
    banner();
    window.dispatchEvent(new Event("aiquant:page-suspended"));
    document.querySelectorAll(".section-loading").forEach((section) => {
      section.classList.remove("section-loading"); section.classList.add("section-cancelled");
    });
  };
  const activate = (next) => {
    if (next && next.owner === state.owner && next.revision < state.revision) return;
    if (next && (next.owner !== state.owner || next.revision !== state.revision)) {
      abort(); state = {...next};
    } else if (!active && !next) state = {...state, revision: state.revision + 1};
    active = true;
    signal("activate");
    banner();
    window.dispatchEvent(new Event("aiquant:page-resumed"));
  };
  window.aiquantPageWork = {activate, deactivate, get state() { return {...state}; }, get active() { return active; }};
  const isWork = (url) => url.origin === location.origin &&
    ((/\/gradio_api\//.test(url.pathname) && !/\/heartbeat\//.test(url.pathname)) ||
      /\/api\/.*\/(?:stream|events|preview)/.test(url.pathname) || /\/file-previews\//.test(url.pathname));
  window.fetch = async (input, options = {}) => {
    const url = new URL(input instanceof Request ? input.url : input, location.href);
    if (!isWork(url)) return nativeFetch(input, options);
    if (!active) throw new DOMException("Page navigation cancelled the request", "AbortError");
    const ticket = state.revision, controller = new AbortController();
    cancelledViews.delete(state.view); banner();
    controllers.set(controller, url);
    const original = options.signal || (input instanceof Request ? input.signal : null);
    const stop = () => controller.abort();
    if (original?.aborted) stop(); else original?.addEventListener("abort", stop, {once: true});
    const headers = new Headers(options.headers || (input instanceof Request ? input.headers : undefined));
    headers.set("x-aiquant-page", state.owner); headers.set("x-aiquant-revision", String(ticket));
    try {
      const response = await nativeFetch(input, {...options, headers, signal: controller.signal});
      if (url.pathname.endsWith("/queue/join")) {
        const body = typeof options.body === "string" ? JSON.parse(options.body) : null;
        const result = await response.clone().json();
        if (body && result.event_id) queued.set(result.event_id, {
          url: url.href.replace("/queue/join", "/cancel"),
          body: {session_hash: body.session_hash, fn_index: body.fn_index, event_id: result.event_id},
        });
      }
      if (!active || ticket !== state.revision) throw new DOMException("Stale page result", "AbortError");
      // Keep streaming bodies abortable until consumed; completed responses retain no controllers.
      for (const method of ["json", "text", "arrayBuffer", "blob", "formData"]) {
        const consume = response[method].bind(response);
        response[method] = async (...values) => {
          try { return await consume(...values); } finally { controllers.delete(controller); }
        };
      }
      if (response.body) {
        const getReader = response.body.getReader.bind(response.body);
        response.body.getReader = (...values) => {
          const reader = getReader(...values), read = reader.read.bind(reader);
          const decoder = new TextDecoder();
          let prefixBuffer = "", startOfEvent = true;
          reader.read = async (...items) => {
            try {
              const value = await read(...items);
              if (url.pathname.endsWith("/queue/data") && value.value) {
                // Event identity precedes large output payloads. Inspect only its bounded prefix.
                const chunk = decoder.decode(value.value, {stream: true});
                const parts = chunk.split("\n\n");
                for (let index = 0; index < parts.length; index++) {
                  if (startOfEvent) prefixBuffer = (prefixBuffer + parts[index]).slice(0, __EVENT_PREFIX_CHARS__);
                  const match = prefixBuffer.match(/"msg"\s*:\s*"process_completed"[^\n]*?"event_id"\s*:\s*"([^"]+)"/);
                  if (match) queued.delete(match[1]);
                  if (index < parts.length - 1) { prefixBuffer = ""; startOfEvent = true; }
                  else if (prefixBuffer.length >= __EVENT_PREFIX_CHARS__) startOfEvent = false;
                }
              }
              if (value.done) controllers.delete(controller);
              return value;
            } catch (error) { controllers.delete(controller); throw error; }
          };
          return reader;
        };
      } else controllers.delete(controller);
      return response;
    } catch (error) { controllers.delete(controller); throw error; }
    finally { original?.removeEventListener("abort", stop); }
  };
  window.EventSource = class extends NativeEventSource {
    constructor(input, options) {
      const url = new URL(input, location.href);
      if (isWork(url)) {
        url.searchParams.set("page_owner", state.owner);
        url.searchParams.set("page_revision", state.revision);
      }
      super(url, options);
      if (isWork(url)) {
        streams.add(this);
        if (!active) this.close();
      }
    }
    close() { streams.delete(this); super.close(); }
  };
  // Gradio timers can continue while cached iframes are hidden. Skip their work there.
  const nativeInterval = window.setInterval.bind(window);
  window.setInterval = (fn, delay, ...args) => nativeInterval((...values) => {
    if (active && typeof fn === "function") fn(...values);
  }, delay, ...args);
  nativeInterval(() => { if (active) signal("activate"); }, __HEARTBEAT_MS__);
  window.addEventListener("pagehide", deactivate);
  window.addEventListener("pageshow", (event) => { if (event.persisted && !embedded) activate(); });
  document.addEventListener("DOMContentLoaded", banner, {once: true});
  window.addEventListener("message", (event) => {
    if (event.origin !== location.origin || event.source !== parent || !embedded) return;
    if (preview) {
      if (event.data?.type === "aiquant:preview-suspend") deactivate();
      if (event.data?.type === "aiquant:preview-resume" && !active) activate();
      return;
    }
    if (event.data?.type === "aiquant:deactivate" && (!event.data.revision || event.data.revision === state.revision)) deactivate();
    if (event.data?.type === "aiquant:select-view" && event.data.page_scope) activate(event.data.page_scope);
  });
  // A frame can finish loading after its parent has already selected another module.
  if (embedded && (preview ? !parent.aiquantPageWork?.active :
      parentScope()?.module !== location.pathname.match(/\/app\/([^/]+)/)?.[1] ||
      parentScope()?.revision !== state.revision)) deactivate();
  else activate();
})();
