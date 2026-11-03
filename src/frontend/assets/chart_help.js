(async () => {
  const response = await fetch(document.currentScript.dataset.catalogUrl, { cache: 'force-cache' });
  if (!response.ok) return;
  const payload = (await response.json()).data;
  const catalog = { default: payload.default, ...payload.charts };
  let pending = false;
  const apply = () => {
    pending = false;
    document.querySelectorAll('.has-chart-help').forEach((element) => {
      if (element.querySelector('.chart-explanation')) return;
      const key = Array.from(element.classList).find(value => value.startsWith('chart-help-key-'))?.slice('chart-help-key-'.length);
      const info = catalog[key] || catalog.default;
      const caption = document.createElement('section');
      caption.className = 'chart-explanation';
      const short = document.createElement('p');
      short.textContent = info.short;
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = 'ⓘ 图表说明';
      summary.title = info.short;
      summary.setAttribute('aria-label', '展开图表说明');
      const body = document.createElement('p');
      body.textContent = info.detail;
      details.append(summary, body);
      caption.append(short, details);
      element.append(caption);
    });
  };
  const schedule = () => {
    if (!pending) { pending = true; requestAnimationFrame(apply); }
  };
  new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
  schedule();
})();
