import { mount, unmount, flushSync } from "svelte";
import Root from "./Root.svelte";
import type { Payload, Send, GraphPatch } from "./types";
import "@xyflow/svelte/dist/style.css";
import "./style.css";

class GraphHost extends HTMLElement {
  cleanup?: () => void;
  disconnectedCallback() {
    this.cleanup?.();
  }
}
if (!customElements.get("aiquant-strategy-graph"))
  customElements.define("aiquant-strategy-graph", GraphHost);

export function mountGraph(host: GraphHost, initial: Payload, send: Send) {
  const app = mount(Root, { target: host, props: { initial, send } });
  flushSync();
  let destroyed = false;
  const destroy = () => {
    if (!destroyed) {
      destroyed = true;
      void unmount(app);
    }
  };
  host.cleanup = destroy;
  return {
    update: (value: GraphPatch) => {
      if (!destroyed) app.update(value);
    },
    destroy,
  };
}
