const id = document.body.dataset.fileId, prefix = document.body.dataset.api;
const endpoint = `${prefix}/file-previews/${id}`;
const element = (name) => document.getElementById(name);
const status = (message, error=false) => { element("reader-status").textContent = message; element("reader-status").classList.toggle("error",error); };
let record, dirty = false, editing = false, markdown;
const announce = () => window.parent.postMessage({type:"aiquant:preview-dirty", dirty}, location.origin);
const api = async (url, options={}) => {
  const response = await fetch(url, {credentials:"same-origin", ...options});
  const value = await response.json();
  if (!response.ok || value.code !== 0) throw new Error(value.message || value.detail || "文件操作失败");
  return value.data;
};
function theme(value) {
  const selected = value || localStorage.getItem("all-in-one-ui-theme") || "light";
  document.documentElement.dataset.theme = selected === "dark" || (selected === "system" && matchMedia("(prefers-color-scheme:dark)").matches) ? "dark":"light";
}
theme();
window.addEventListener("message", (event) => {
  if (event.origin === location.origin && event.source === window.parent && event.data?.type === "aiquant:theme") theme(event.data.theme);
});
async function markdownEngine() {
  if (!window.markdownit) await new Promise((resolve,reject) => {
    const script = document.createElement("script"); script.src = "/static/vendor/markdown-it/markdown-it.umd.min.js";
    script.onload = resolve; script.onerror = () => reject(new Error("Markdown阅读资源未安装")); document.head.append(script);
  });
  return window.markdownit({html:false, linkify:false, typographer:false});
}
function renderMarkdown() {
  element("markdown-preview").innerHTML = markdown.render(element("markdown-editor").value);
  element("markdown-preview").querySelectorAll("img").forEach((image) => {
    const path = image.getAttribute("src") || "";
    if (/^(https?:|data:|blob:|\/\/)/i.test(path)) { image.removeAttribute("src"); image.alt += "（外部图片未加载）"; return; }
    const segments = path.split("/").map(encodeURIComponent).join("/");
    image.src = `${endpoint}/assets/${segments}`;
  });
  element("markdown-preview").querySelectorAll("a").forEach((link) => { link.target="_blank"; link.rel="noopener noreferrer"; });
}
const safeAction = (action) => async () => { try { await action(); } catch(error) {status(error.message,true);} };
async function showOffice() {
  let result = await api(endpoint+"/conversion", {method:"POST"});
  while(["running","queued"].includes(result.status)) {
    status(result.status === "queued"?"Office转换任务排队中…":"Office文件正在转换为只读PDF，完成后自动展示…");
    await new Promise((resolve) => setTimeout(resolve, record.limits.conversion_poll_ms));
    result = await api(endpoint+"/conversion", {method:"POST"});
  }
  if (result.status !== "completed") throw new Error(result.error || "Office预览失败，仍可下载原件");
  await (await import("./pdf_reader.js")).openPdf(endpoint+"/pdf",record.limits,status);
  status("Office只读预览 · 已完成转换，后续打开复用缓存；复杂版式可能存在差异");
}
async function load() {
  record = await api(endpoint);
  element("file-title").textContent = record.name;
  element("file-meta").textContent = `${record.ui.kind_labels[record.kind]} · ${(record.bytes/1024).toFixed(1)} KB · ${record.ui.source_labels[record.source]} · ${record.editable?record.ui.editable:record.ui.readonly}`;
  element("download-file").href = endpoint+"/raw?download=true";
  status(record.legacy?record.ui.legacy:record.editable?"Markdown可编辑，修改后需要保存":"只读文件预览");
  if (record.preview_truncated) status("文件较大，当前只读展示部分正文；可下载完整原件");
  element("edit-file").hidden = !record.editable;
  if (record.kind === "markdown") {
    markdown = await markdownEngine(); element("markdown-layout").hidden=false;
    element("markdown-editor").value = record.content; renderMarkdown();
  } else if (record.kind === "html") {
    status("HTML静态阅读；文件自带脚本和外部资源未运行");
    const parser = new DOMParser().parseFromString(record.content,"text/html");
    parser.querySelectorAll("script,iframe,object,embed,base,form,meta[http-equiv],link").forEach((node) => node.remove());
    const policy = parser.createElement("meta"); policy.httpEquiv="Content-Security-Policy";
    policy.content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:;";
    parser.head.prepend(policy);
    element("html-preview").srcdoc = "<!doctype html>"+parser.documentElement.outerHTML;
    element("html-preview").hidden = false;
  } else if (record.kind === "image") {
    element("image-preview").src=endpoint+"/raw"; element("image-preview").hidden=false;
  } else if (record.kind === "pdf") {
    await (await import("./pdf_reader.js")).openPdf(endpoint+"/raw",record.limits,status);
  } else if (record.kind === "office") {
    await showOffice();
  } else {
    element("text-preview").textContent = record.content; element("text-preview").hidden=false;
  }
}
element("edit-file").onclick = () => {
  editing=!editing; element("markdown-editor").hidden=!editing;
  element("markdown-layout").classList.toggle("editing",editing);
  element("save-file").hidden=!editing; element("edit-file").textContent=editing?"阅读模式":"编辑Markdown";
};
element("markdown-editor").oninput = () => {
  dirty=element("markdown-editor").value!==record.content; announce(); renderMarkdown();
  status(dirty?"有未保存修改":"内容未变化");
};
element("save-file").onclick = safeAction(async () => {
  element("save-file").disabled=true;
  try {
    record=await api(endpoint+"/markdown", {method:"PUT",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({revision:record.revision,content:element("markdown-editor").value})});
    dirty=false; announce(); status("已保存Markdown，新版本已生效");
  } finally {element("save-file").disabled=false;}
});
element("reload-file").onclick = () => {
  if (!dirty || confirm(record.ui.unsaved)) {dirty=false;announce();location.reload();}
};
element("fullscreen").onclick = safeAction(() => document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen());
document.addEventListener("fullscreenchange", () => {element("fullscreen").textContent = document.fullscreenElement?"退出全屏":"全屏";});
window.addEventListener("beforeunload", (event) => {if(dirty && parent===window){event.preventDefault();event.returnValue="";}});
function locateCitation() {
  const quote = new URLSearchParams(location.hash.slice(1)).get("quote");
  if (!quote) return;
  if (record.kind === "pdf" || record.kind === "office") {
    element("pdf-search").value = quote; element("search-pdf").click(); return;
  }
  const root = record.kind === "markdown" ? element("markdown-preview") : element("text-preview");
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode, offset = node.textContent.indexOf(quote);
    if (offset < 0) continue;
    const range = document.createRange(); range.setStart(node,offset); range.setEnd(node,offset+quote.length);
    const mark = document.createElement("mark"); range.surroundContents(mark);
    mark.scrollIntoView({block:"center"}); break;
  }
}
load().then(locateCitation).catch((error) => status(error.message,true));
