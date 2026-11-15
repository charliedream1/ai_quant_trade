// Pointer resizing and header dragging preserve panel bounds independently of its launcher.
(() => {
  const cfg = __ASSISTANT_LAYOUT__;
  const attach = () => {
    const panel = document.getElementById("ai-floating-panel");
    if (!panel || panel.dataset.resizeReady) return Boolean(panel);
    panel.dataset.resizeReady = "1";
    const limit = (value, minimum, maximum) => Math.max(Math.min(minimum, maximum), Math.min(value, maximum));
    const size = (width, height) => {
      panel.style.setProperty("width", `${limit(width, cfg.min_width, innerWidth - 2 * cfg.viewport_margin)}px`, "important");
      panel.style.setProperty("height", `${limit(height, cfg.min_height, innerHeight - 2 * cfg.viewport_margin)}px`, "important");
      panel.style.setProperty("max-height", `${innerHeight - 2 * cfg.viewport_margin}px`, "important");
    };
    let stored;
    try { stored = JSON.parse(localStorage.getItem(cfg.storage_key)); } catch { stored = null; }
    size(Number(stored?.width) || cfg.width, Number(stored?.height) || cfg.height);
    const persist = () => {
      const rect = panel.getBoundingClientRect();
      localStorage.setItem(cfg.storage_key, JSON.stringify({width: rect.width, height: rect.height}));
      window.dispatchEvent(new Event("resize"));
    };
    const handle = document.createElement("button");
    handle.type = "button"; handle.className = "assistant-resize-handle";
    handle.setAttribute("aria-label", cfg.messages.resize); handle.title = cfg.messages.resize;
    handle.textContent = "⤡"; panel.append(handle);
    const bind = (element, resizing) => {
      let origin;
      element.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || (!resizing && event.target.closest("button"))) return;
        event.preventDefault(); const rect = panel.getBoundingClientRect();
        origin = {x: event.clientX, y: event.clientY, rect};
        element.setPointerCapture(event.pointerId);
      });
      element.addEventListener("pointermove", (event) => {
        if (!origin) return;
        const dx = event.clientX - origin.x, dy = event.clientY - origin.y;
        if (resizing) size(origin.rect.width + dx, origin.rect.height + dy);
        else {
          panel.style.left = `${limit(origin.rect.left + dx, cfg.viewport_margin, innerWidth - origin.rect.width - cfg.viewport_margin)}px`;
          panel.style.top = `${limit(origin.rect.top + dy, cfg.viewport_margin, innerHeight - origin.rect.height - cfg.viewport_margin)}px`;
          panel.style.right = panel.style.bottom = "auto";
        }
      });
      element.addEventListener("pointerup", () => { if (origin) persist(); origin = null; });
      element.addEventListener("pointercancel", () => { origin = null; });
    };
    bind(handle, true); bind(panel.querySelector(".ai-panel-header"), false);
    handle.addEventListener("keydown", (event) => {
      if (!event.key.startsWith("Arrow")) return;
      event.preventDefault(); const rect = panel.getBoundingClientRect();
      const step = cfg.viewport_margin;
      size(rect.width + (event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0),
        rect.height + (event.key === "ArrowDown" ? step : event.key === "ArrowUp" ? -step : 0)); persist();
    });
    window.addEventListener("resize", () => {
      size(parseFloat(panel.style.width) || cfg.width, parseFloat(panel.style.height) || cfg.height);
    });
    return true;
  };
  if (!attach()) {
    const observer = new MutationObserver(() => { if (attach()) observer.disconnect(); });
    observer.observe(document.body, {childList: true, subtree: true});
  }
})();
