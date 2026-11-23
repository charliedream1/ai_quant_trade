const host = element.querySelector('aiquant-strategy-graph');
let controller;
const pending = [];
const deliver = (patch) => {
  if (!patch) return;
  if (controller) controller.update(patch);
  else pending.push(patch);
};
if (typeof watch === 'function') {
  watch('patch', () => deliver(props.patch));
} else {
  // Gradio 6.3 forwards custom props through its component proxy.
  let patch = props.patch;
  Object.defineProperty(props, 'patch', {
    enumerable: true,
    get: () => patch,
    set: (next) => {
      patch = next;
      queueMicrotask(() => deliver(next));
    },
  });
}
deliver(props.patch);
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
}).catch(() => { host.textContent = props.load_failed; host.setAttribute('role', 'alert'); });
