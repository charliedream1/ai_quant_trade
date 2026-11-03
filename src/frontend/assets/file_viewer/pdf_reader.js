export function searchableText(items, tolerance) {
  const chunks = items.filter((item) => item.str?.trim() && item.transform)
    .sort((a,b) => b.transform[5]-a.transform[5] || a.transform[4]-b.transform[4]);
  const lines = [];
  for (const item of chunks) {
    let line = lines.at(-1);
    if (!line || Math.abs(line.y-item.transform[5]) > Math.max(line.height,item.height)*tolerance) {
      line = {y:item.transform[5],height:item.height,items:[]}; lines.push(line);
    }
    line.items.push(item);
  }
  return lines.map((line) => line.items.sort((a,b) => a.transform[4]-b.transform[4])
    .map((item) => item.str).join("")).join("\n").normalize("NFKC").replace(/\s+/g,"").toLocaleLowerCase();
}

export async function openPdf(url, limits, status) {
  const library = await import("/static/vendor/pdfjs/build/pdf.mjs");
  const root = "/static/vendor/pdfjs/";
  library.GlobalWorkerOptions.workerSrc = root + "build/pdf.worker.mjs";
  const task = library.getDocument({url, cMapUrl:root+"web/cmaps/", cMapPacked:true,
    standardFontDataUrl:root+"web/standard_fonts/", wasmUrl:root+"web/wasm/", iccUrl:root+"web/iccs/"});
  const pdf = await task.promise;
  if (pdf.numPages > limits.max_pdf_pages) { await task.destroy(); throw new Error("PDF页数超过预览上限，请下载阅读"); }
  const canvas = document.getElementById("pdf-canvas"), layout = document.getElementById("pdf-layout");
  const position = document.getElementById("page-position");
  document.getElementById("pdf-toolbar").hidden = layout.hidden = false;
  let pageNumber = 1, zoom = null, pageWidth = 1, renderTask, sequence = 0, searchPage = 0, previousQuery = "";
  const draw = async () => {
    const ticket = ++sequence;
    renderTask?.cancel();
    if (renderTask) await renderTask.promise.catch(() => {});
    const page = await pdf.getPage(pageNumber);
    if (ticket !== sequence) return;
    const base = page.getViewport({scale:1});
    pageWidth = base.width;
    const fit = Math.max(limits.pdf_min_zoom, (document.getElementById("reader-content").clientWidth - 40) / base.width);
    const viewport = page.getViewport({scale:zoom ?? fit});
    canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
    position.textContent = `${pageNumber} / ${pdf.numPages} 页`;
    document.getElementById("page-prev").disabled = pageNumber === 1;
    document.getElementById("page-next").disabled = pageNumber === pdf.numPages;
    renderTask = page.render({canvasContext:canvas.getContext("2d"), viewport});
    try { await renderTask.promise; } catch(error) { if (error.name !== "RenderingCancelledException") throw error; }
  };
  const run = (action) => () => Promise.resolve(action()).catch((error) => status(error.message, true));
  document.getElementById("page-prev").onclick = run(() => { pageNumber = Math.max(1,pageNumber-1); return draw(); });
  document.getElementById("page-next").onclick = run(() => { pageNumber = Math.min(pdf.numPages,pageNumber+1); return draw(); });
  document.getElementById("zoom-fit").onclick = run(() => { zoom = null; return draw(); });
  const resize = (direction) => {
    zoom = Math.max(limits.pdf_min_zoom, Math.min(limits.pdf_max_zoom,
      (zoom ?? canvas.width / pageWidth) + limits.pdf_zoom_step * direction));
    return draw();
  };
  document.getElementById("zoom-in").onclick = run(() => resize(1));
  document.getElementById("zoom-out").onclick = run(() => resize(-1));
  document.getElementById("search-pdf").onclick = run(async () => {
    const query = document.getElementById("pdf-search").value.trim().normalize("NFKC").replace(/\s+/g,"").toLocaleLowerCase();
    if (!query) return;
    if (query !== previousQuery) { searchPage = 0; previousQuery = query; }
    const output = document.getElementById("search-result"); output.textContent = "查找中…";
    for (let offset=1; offset<=pdf.numPages; offset++) {
      const number = (searchPage + offset - 1) % pdf.numPages + 1;
      const page = await pdf.getPage(number), text = await page.getTextContent();
      if (searchableText(text.items,limits.pdf_line_tolerance).includes(query)) {
        pageNumber = searchPage = number; output.textContent = `第 ${number} 页匹配`; await draw(); return;
      }
    }
    output.textContent = "未找到；扫描页面可能没有文字层";
  });
  document.getElementById("pdf-search").onkeydown = (event) => {
    if (event.key === "Enter") document.getElementById("search-pdf").click();
  };
  window.addEventListener("pagehide", () => { renderTask?.cancel(); task.destroy(); }, {once:true});
  await draw();
}
