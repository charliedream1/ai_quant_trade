(() => {
  if (window.__filePreviewPanelBound) return;
  window.__filePreviewPanelBound = true;
  let panel, frame, dirty = false;
  const notify = () => { if (parent !== window) parent.postMessage({type:"aiquant:preview-dirty-state",dirty},location.origin); };
  const seen = new Set();
  const allowed = (url) => url.origin === location.origin && /\/file-previews\/[a-f0-9]{32}\/view$/.test(url.pathname);
  const discard = () => !dirty || confirm("Markdown有未保存修改，是否放弃修改？");
  const close = () => {
    if (!discard()) return;
    panel?.remove(); panel = frame = null; dirty = false; notify(); document.documentElement.classList.remove("file-reader-open");
  };
  const open = (href) => {
    const url = new URL(href, location.origin);
    if (!allowed(url) || !discard()) return;
    panel?.remove(); dirty = false; notify();
    panel = document.createElement("aside");
    panel.className = "file-reader-panel";
    if (new URLSearchParams(url.hash.slice(1)).get("side") === "left") panel.classList.add("file-reader-panel-left");
    panel.setAttribute("aria-label", "文件阅读面板");
    const header = document.createElement("div"); header.className = "file-reader-panel-header";
    const title = document.createElement("strong"); title.textContent = "文件阅读";
    const button = document.createElement("button"); button.type = "button"; button.textContent = "关闭 ×";
    button.setAttribute("aria-label", "关闭文件阅读"); button.addEventListener("click", close);
    header.append(title, button);
    frame = document.createElement("iframe"); frame.title = "文件阅读与Markdown编辑";
    frame.allowFullscreen = true; frame.src = url.href;
    panel.append(header, frame); document.body.append(panel); document.documentElement.classList.add("file-reader-open");
  };
  document.addEventListener("click", (event) => {
    const link = event.target.closest?.("a[href*='/file-previews/']");
    if (!link || !allowed(new URL(link.href))) return;
    event.preventDefault(); event.stopPropagation(); open(link.href);
  }, true);
  window.addEventListener("message", (event) => {
    if (event.origin !== location.origin) return;
    if (event.data?.type === "aiquant:theme") frame?.contentWindow.postMessage(event.data, location.origin);
    if (event.source === frame?.contentWindow && event.data?.type === "aiquant:preview-dirty") { dirty = Boolean(event.data.dirty); notify(); }
    if (event.source === parent && event.data?.type === "aiquant:preview-discard") {dirty=false;close();}
  });
  window.addEventListener("beforeunload", (event) => {if(dirty){event.preventDefault();event.returnValue="";}});
  const check = (root) => {
    const nodes = [];
    if (root.matches?.("[data-preview-auto]")) nodes.push(root);
    root.querySelectorAll?.("[data-preview-auto]").forEach((node) => nodes.push(node));
    nodes.forEach((node) => {
      if (!node.closest("#reader-upload-result,#ai-file-reader,#kb-file-reader,#alpha-file-reader,#rag-file-reader")) return;
      const key = node.dataset.previewAuto;
      if (seen.has(key)) return;
      seen.add(key); open(node.href);
    });
  };
  const style = document.createElement("style");
  style.textContent = `.file-reader-panel{position:fixed;inset:0 0 0 auto;width:min(1040px,92vw);z-index:10000;display:flex;flex-direction:column;background:#f2f6fc;border-left:1px solid #d6dfef;box-shadow:-12px 0 45px #1b34503a}.file-reader-panel-header{display:flex;justify-content:flex-start;gap:16px;align-items:center;padding:9px 16px;color:#243754;background:#f7faff;border-bottom:1px solid #dde6f1}.file-reader-panel-header button{border:1px solid #dce5f2;border-radius:8px;background:white;padding:5px 12px;cursor:pointer}.file-reader-panel iframe{width:100%;flex:1;min-height:0;border:0}`;
  style.textContent += `html[data-theme="dark"] .file-reader-panel{background:#101a29;border-color:#354960}html[data-theme="dark"] .file-reader-panel-header{color:#e0eafa;background:#19283b;border-color:#354960}html[data-theme="dark"] .file-reader-panel-header button{color:#e0eafa;background:#20334b;border-color:#354960}.file-reader-open #ai-floating-button,.file-reader-open #ai-floating-panel{display:none!important}`;
  style.textContent += `.file-reader-panel.file-reader-panel-left{inset:0 auto 0 0;width:50vw;border-left:0;border-right:1px solid #d6dfef}@media(max-width:700px){.file-reader-panel.file-reader-panel-left{width:100vw}}`;
  document.head.append(style);
  check(document);
  new MutationObserver((changes) => changes.forEach((change) => {
    if (change.type === "attributes") check(change.target);
    change.addedNodes.forEach((node) => {
      if (node.nodeType === Node.ELEMENT_NODE) check(node);
      else if (node.parentElement) check(node.parentElement);
    });
  })).observe(document.body, {childList:true, subtree:true, attributes:true, attributeFilter:["href","data-preview-auto"]});
})();
