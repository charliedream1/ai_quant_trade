const host = element.querySelector('aiquant-strategy-graph');
let controller;
const pending = [];
watch('patch', () => {
  if (!props.patch) return;
  if (controller) controller.update(props.patch);
  else pending.push(props.patch);
});
const base = props.assets_path;
if (!document.querySelector(`link[data-strategy-graph="${base}"]`)) {
  const css = document.createElement('link');
  css.rel = 'stylesheet'; css.href = `${base}/graph.css?v=${props.assets_version}`; css.dataset.strategyGraph = base;
  document.head.appendChild(css);
}
import(`${base}/graph.js?v=${props.assets_version}`).then(module => {
  if (!host.isConnected) return;
  controller = module.mountGraph(host, props.value, (kind, value) => {
    props.value = value;
    queueMicrotask(() => {
      if (kind === 'apply') trigger('submit');
      if (kind === 'layout') trigger('input');
    });
  });
  for (const patch of pending.splice(0)) controller.update(patch);
  trigger('load');
}).catch(error => { host.textContent = String(error); host.setAttribute('role', 'alert'); });
