// The module iframe owns its height and its optional local panels.
(() => {
  const sidebarKey = "all-in-one-ai-sidebar-collapsed";
  let scheduled = false;
  const visible = (el) => Boolean(el && el.getClientRects().length && getComputedStyle(el).display !== "none");
  const update = () => {
    scheduled = false;
    const shell = document.getElementById("ai-console-shell");
    const active = visible(shell);
    document.documentElement.classList.toggle("ai-console-active", active);
    if (!active) return;
    // Gradio may scroll an outer container when focusing a control; keep the workspace anchored.
    for (let parent = shell.parentElement; parent; parent = parent.parentElement) {
      if (parent.scrollTop) parent.scrollTop = 0;
      if (parent.scrollLeft) parent.scrollLeft = 0;
    }
    if (shell.dataset.layoutInitialized !== "1") {
      shell.dataset.layoutInitialized = "1";
      const saved = localStorage.getItem(sidebarKey);
      shell.classList.toggle("console-sidebar-collapsed", saved === "1" || (saved === null && innerWidth <= 760));
    }
    const top = Math.max(0, shell.getBoundingClientRect().top);
    const height = `${Math.max(0, innerHeight - top - 8)}px`;
    if (shell.style.getPropertyValue("--ai-console-height") !== height) shell.style.setProperty("--ai-console-height", height);
    shell.classList.toggle("chat-active", visible(document.getElementById("ai-console-chat-page")));
    const sidebar = document.getElementById("ai-console-sidebar-toggle");
    if (sidebar) {
      const collapsed = shell.classList.contains("console-sidebar-collapsed");
      const label = collapsed ? "展开工作栏" : "收起工作栏";
      sidebar.setAttribute("aria-label", label);
      sidebar.setAttribute("aria-expanded", String(!collapsed));
      const text = sidebar.querySelector("span:last-child");
      if (text && text.textContent !== label) text.textContent = label;
    }
    const files = document.getElementById("ai-console-files-toggle");
    if (files) {
      const opened = shell.classList.contains("files-open");
      const label = opened ? "收起文件面板" : "打开文件面板";
      if (files.textContent !== label) files.textContent = label;
      files.setAttribute("aria-expanded", String(opened));
    }
    const composerHints = {
      "ai-console-attachments": "添加文件或图片；也可以直接拖入附件",
      "ai-console-backend": "选择实际运行后台；未接入的 CLI 会明确提示",
      "ai-console-model": "选择已启用模型；空值表示系统默认模型",
      "ai-console-reasoning": "选择思考强度；是否生效取决于后台和模型",
      "ai-console-send": "发送当前任务（Enter 发送，Ctrl+Enter 换行）",
    };
    Object.entries(composerHints).forEach(([id, hint]) => {
      const element = document.getElementById(id);
      if (element) {
        element.setAttribute("title", hint);
        if (id === "ai-console-send") element.setAttribute("aria-label", "发送");
      }
    });
  };
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(update);
  };
  document.addEventListener("keydown", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLTextAreaElement)) return;
    if (event.key !== "Enter") return;
    const submit = target.closest("#ai-console-input")
      ? document.getElementById("ai-console-send")
      : target.closest("#ai-chat-input")
        ? document.getElementById("ai-chat-send")
        : target.closest("#ai-cli-requirement")
          ? document.getElementById("ai-cli-build")
          : null;
    if (!submit) return;
    if (event.isComposing || event.keyCode === 229) {
      event.stopImmediatePropagation();
      return;
    }
    if (event.altKey || event.metaKey || event.repeat) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    if (event.ctrlKey || event.shiftKey) {
      target.setRangeText("\n", target.selectionStart, target.selectionEnd, "end");
      target.dispatchEvent(new Event("input", {bubbles:true}));
      return;
    }
    submit.click();
  }, true);
  document.addEventListener("click", (event) => {
    const shell = document.getElementById("ai-console-shell");
    if (!shell) return;
    if (event.target.closest("#ai-console-sidebar-toggle")) {
      const collapsed = shell.classList.toggle("console-sidebar-collapsed");
      localStorage.setItem(sidebarKey, collapsed ? "1" : "0");
    }
    if (event.target.closest("#ai-console-sidebar-close")) {
      shell.classList.add("console-sidebar-collapsed");
      localStorage.setItem(sidebarKey, "1");
    }
    if (event.target.closest("#ai-console-files-toggle")) shell.classList.toggle("files-open");
    if (event.target.closest("#ai-console-files-close")) shell.classList.remove("files-open");
    schedule();
  });
  addEventListener("resize", schedule);
  document.addEventListener("scroll", (event) => {
    const shell = document.getElementById("ai-console-shell");
    if (shell && (event.target === document || (event.target instanceof Element && event.target.contains(shell)))) schedule();
  }, true);
  addEventListener("message", (event) => {
    if (event.origin === location.origin && event.data?.type === "aiquant:resize") schedule();
  });
  new MutationObserver(schedule).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ["class", "style"]});
  schedule();
})();
