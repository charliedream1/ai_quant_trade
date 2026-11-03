<script lang="ts">
  import {
    SvelteFlow,
    Controls,
    MiniMap,
    Background,
    useSvelteFlow,
    type Edge,
    type Connection,
    type Viewport,
  } from "@xyflow/svelte";
  import { tick, untrack, onMount } from "svelte";
  import StrategyNode from "./StrategyNode.svelte";
  import Properties from "./Properties.svelte";
  import { readDocument, downloadDocument } from "./files";
  import { mergeGraphUpdate } from "./updates";
  import { viewportFitter } from "./viewport";
  import {
    copy,
    scoped,
    scopeKey,
    graph,
    fields,
    canConnect,
    connect,
    disconnect,
    addStage,
    newId,
  } from "./documents";
  import type {
    Payload,
    VisualNode,
    Definition,
    Send,
    GraphPatch,
  } from "./types";

  let { initial, send }: { initial: Payload; send: Send } = $props();
  let payload = $state<Payload>(untrack(() => copy(initial))),
    path = $state<string[]>([]),
    selected = $state(""),
    search = $state("");
  let nodes = $state<VisualNode[]>([]),
    edges = $state<Edge[]>([]),
    message = $state(""),
    dirty = $state(false),
    selectedEdge = $state("");
  let undo = $state<Definition[]>([]),
    redo = $state<Definition[]>([]),
    menu = $state(true),
    fullscreen = $state(false);
  let root: HTMLDivElement;
  let canvas: HTMLDivElement;
  let fitter: ReturnType<typeof viewportFitter> | undefined;
  const navigationTimes: number[] = [];
  function recordNavigation(start: number) {
    void tick().then(() => {
      navigationTimes.push(performance.now() - start);
      navigationTimes.splice(
        0,
        Math.max(
          0,
          navigationTimes.length -
            Number(payload.config.limits.performance_samples),
        ),
      );
      if (root) root.dataset.navigationTimes = JSON.stringify(navigationTimes);
    });
  }
  const flow = useSvelteFlow();
  const ui = $derived(payload.config.ui),
    plan = $derived(scoped(payload.document, path));
  const nodeTypes = { strategy: StrategyNode };
  const stale = $derived(
    payload.evidence.definition_digest &&
      payload.compiled_digest !== payload.evidence.definition_digest,
  );

  function capture() {
    const key = scopeKey(path);
    payload.layout[key] = {
      positions: Object.fromEntries(nodes.map((n) => [n.id, n.position])),
      viewport: flow.getViewport(),
      selected,
    };
  }
  function refresh(fit = false) {
    const next = graph(payload, path);
    nodes = next.nodes.map((n) => ({ ...n, selected: n.id === selected }));
    if (selected && !nodes.some((n) => n.id === selected)) selected = "";
    edges = next.edges;
    highlight();
    if (fit) void tick().then(() => fitter?.request());
  }
  function remember() {
    capture();
    payload.edit_revision += 1;
    undo = [...undo, copy(payload.document)].slice(
      -Number(payload.config.limits.undo_steps),
    );
    redo = [];
    dirty = true;
    payload.compiled_digest = "";
    message = ui.modified;
  }
  function edit(action: () => void) {
    remember();
    try {
      action();
      refresh();
      send("draft", copy(payload));
    } catch (e) {
      message = String(e);
    }
  }
  function highlight() {
    const related = new Set([selected]);
    const walk = (id: string, up: boolean) => {
      for (const edge of edges.filter(
        (e) => !e.data?.context && (up ? e.target : e.source) === id,
      )) {
        const next = up ? edge.source : edge.target;
        if (!related.has(next)) {
          related.add(next);
          walk(next, up);
        }
      }
    };
    if (selected) {
      walk(selected, true);
      walk(selected, false);
    }
    nodes = nodes.map((n) => ({
      ...n,
      selected: n.id === selected,
      class: selected && !related.has(n.id) ? "graph-dim" : "",
    }));
    edges = edges.map((e) => ({
      ...e,
      class:
        selected &&
        related.has(e.source) &&
        related.has(e.target) &&
        !e.data?.context
          ? "graph-edge-active"
          : "",
    }));
  }
  function select(id: string, center = true) {
    const started = performance.now();
    selected = id;
    selectedEdge = "";
    highlight();
    const node = nodes.find((n) => n.id === id);
    if (center && node)
      void flow.setCenter(node.position.x + 100, node.position.y + 50, {
        zoom: Math.max(flow.getZoom(), 0.7),
        duration: 0,
      });
    recordNavigation(started);
  }
  function navigate(next: string[], fromHistory = false) {
    const started = performance.now();
    capture();
    path = next;
    selected = payload.layout[scopeKey(path)]?.selected || "";
    refresh();
    const viewport = payload.layout[scopeKey(path)]?.viewport;
    void tick().then(() =>
      viewport
        ? flow.setViewport(viewport, { duration: 0 })
        : flow.fitView({ padding: 0.15, duration: 0 }),
    );
    const url = new URL(location.href);
    url.searchParams.set("node", scopeKey(path));
    if (!fromHistory) history.pushState(null, "", url);
    recordNavigation(started);
  }
  function enter() {
    if (selected.startsWith("s:")) navigate([...path, selected.slice(2)]);
  }
  function updateNode(params: Record<string, unknown>, method: string) {
    edit(() => {
      const current = scoped(payload.document, path),
        node = current.nodes?.find((n) => n.id === selected);
      if (node) node.params = copy(params);
      else if (selected === "@portfolio")
        current.portfolio = { component: method, params: copy(params) };
      else if (selected === "@risk") current.risk = copy(params);
      else if (selected === "@execution") current.execution = copy(params);
    });
  }
  function remove() {
    const current = scoped(payload.document, path);
    if (!current.nodes?.some((n) => n.id === selected)) return;
    edit(() => {
      current.nodes = current.nodes!.filter((n) => n.id !== selected);
      for (const node of current.nodes) disconnect(current, selected, node.id);
      if (current.output === selected) current.output = "universe";
      selected = "";
    });
  }
  function duplicate() {
    const node = plan.nodes?.find((n) => n.id === selected);
    if (!node) return;
    edit(() => {
      const cloned = copy(node);
      cloned.id = newId(plan, node.id + "_copy");
      plan.nodes!.push(cloned);
      selected = cloned.id;
    });
  }
  function connectNodes(connection: Connection) {
    if (!canConnect(plan, payload, connection)) {
      message = ui.invalid_edge;
      return;
    }
    edit(() => connect(plan, payload, connection));
  }
  function undoRedo(back: boolean) {
    capture();
    const stack = back ? undo : redo;
    if (!stack.length) return;
    const next = stack.at(-1)!;
    if (back) {
      redo = [...redo, copy(payload.document)];
      undo = undo.slice(0, -1);
    } else {
      undo = [...undo, copy(payload.document)];
      redo = redo.slice(0, -1);
    }
    payload.document = copy(next);
    payload.edit_revision += 1;
    payload.compiled_digest = "";
    dirty = true;
    refresh();
    send("draft", copy(payload));
  }
  function submit(kind: "apply" | "layout") {
    capture();
    send(kind, copy(payload));
  }
  export function update(next: GraphPatch) {
    const merged = mergeGraphUpdate(payload, next, dirty);
    if (!merged.accepted) return;
    payload = merged.value;
    dirty = merged.dirty;
    if (merged.reset) {
      path = [];
      selected = "";
      selectedEdge = "";
      search = "";
      undo = [];
      redo = [];
      message = ui.no_execute;
    } else if (next.kind === "applied") message = ui.applied;
    else if (next.kind === "layout") message = ui.saved;
    refresh(merged.reset);
    send("draft", copy(payload));
  }
  function searchNode() {
    const query = search.toLowerCase();
    if (!query) return;
    const found = nodes.find((n) =>
      (n.id + " " + n.data.component + " " + n.data.label)
        .toLowerCase()
        .includes(query),
    );
    if (found) {
      select(found.id);
      return;
    }
    let hit: { path: string[]; id: string } | undefined;
    const walk = (doc: Definition, scope: string[]) => {
      for (const node of doc.nodes || [])
        if (
          (node.id + " " + node.component).toLowerCase().includes(query) &&
          !hit
        )
          hit = { path: scope, id: node.id };
      for (const child of doc.sleeves || [])
        walk(child.definition, [...scope, child.id]);
    };
    walk(payload.document, []);
    if (hit) {
      const target = hit;
      navigate(target.path);
      void tick().then(() => select(target.id));
    }
  }
  function arrange() {
    capture();
    delete payload.layout[scopeKey(path)].positions;
    refresh(true);
  }
  function drop(event: DragEvent) {
    event.preventDefault();
    const component = event.dataTransfer?.getData(
      "application/aiquant-component",
    );
    if (!component) return;
    edit(() => {
      const node = addStage(plan, payload, component);
      selected = node.id;
      const point = flow.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      payload.layout[scopeKey(path)] ??= {};
      payload.layout[scopeKey(path)].positions ??= {};
      payload.layout[scopeKey(path)].positions![node.id] = point;
    });
  }
  function exportFile() {
    capture();
    downloadDocument(payload);
  }
  async function importFile(event: Event) {
    try {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const value = await readDocument(file, payload);
      edit(() => {
        payload.document = copy(value.document);
        payload.layout = copy(value.layout || {});
        path = [];
        selected = "";
      });
    } catch (e) {
      message = String(e);
    } finally {
      (event.target as HTMLInputElement).value = "";
    }
  }
  function onKeys(e: KeyboardEvent) {
    if (
      ["INPUT", "TEXTAREA", "SELECT"].includes(
        (e.target as HTMLElement).tagName,
      )
    )
      return;
    if (e.key === "Escape" && path.length) {
      e.preventDefault();
      navigate(path.slice(0, -1));
    }
    if (e.key === "Enter") enter();
    const current = plan.nodes?.find((n) => n.id === selected);
    if (e.altKey && e.key === "ArrowLeft" && current?.inputs?.[0])
      select(current.inputs[0]);
    if (e.altKey && e.key === "ArrowRight") {
      const next = plan.nodes?.find((n) => (n.inputs || []).includes(selected));
      if (next) select(next.id);
    }
    if (e.key === "Delete") remove();
    if ((e.ctrlKey || e.metaKey) && e.key === "z") {
      e.preventDefault();
      undoRedo(!e.shiftKey);
    }
  }
  onMount(() => {
    fitter = viewportFitter(
      canvas,
      Number(payload.config.limits.fit_stable_frames),
      async () => {
        await flow.fitView({
          padding: Number(payload.config.limits.fit_padding),
          duration: 0,
        });
        await tick();
      },
    );
    fitter.request();
    const resize = () => {
      fullscreen = Boolean(document.fullscreenElement);
      refresh(true);
    };
    const restore = () => {
      const key = new URL(location.href).searchParams.get("node");
      const next = (key || "main").split("/").slice(1);
      try {
        scoped(payload.document, next);
        navigate(next, true);
      } catch {
        navigate([], true);
      }
    };
    restore();
    window.addEventListener("popstate", restore);
    document.addEventListener("fullscreenchange", resize);
    return () => {
      window.removeEventListener("popstate", restore);
      document.removeEventListener("fullscreenchange", resize);
      fitter?.destroy();
    };
  });
  refresh();
</script>

<svelte:window
  onkeydown={(event) => {
    if ((event.target as HTMLElement)?.closest(".strategy-graph-app"))
      onKeys(event);
  }}
/>
<div
  class="strategy-graph-app"
  data-doc-id={payload.doc_id}
  role="region"
  aria-label={ui.title}
  bind:this={root}
>
  <div class="graph-toolbar">
    <button onclick={() => (menu = !menu)} aria-label={ui.add}>☷</button>
    <input
      class="graph-search"
      aria-label={ui.search}
      placeholder={ui.search_placeholder}
      bind:value={search}
      onkeydown={(e) => {
        if (e.key === "Enter") searchNode();
      }}
    />
    <button onclick={() => flow.fitView({ padding: 0.15, duration: 0 })}
      >{ui.fit}</button
    ><button onclick={arrange}>{ui.arrange}</button>
    <button disabled={!undo.length} onclick={() => undoRedo(true)}
      >{ui.undo}</button
    ><button disabled={!redo.length} onclick={() => undoRedo(false)}
      >{ui.redo}</button
    >
    <button onclick={() => submit("layout")}>{ui.save_layout}</button><button
      class="graph-primary"
      onclick={() => submit("apply")}>{ui.apply}</button
    >
    <button
      onclick={() =>
        (fullscreen
          ? document.exitFullscreen()
          : root.requestFullscreen()
        ).catch((e) => (message = String(e)))}
      >{fullscreen ? ui.leave_fullscreen : ui.fullscreen}</button
    ><button onclick={exportFile}>{ui.export}</button><label
      class="graph-import"
      >{ui.import}<input
        type="file"
        accept="application/json,.json"
        onchange={importFile}
      /></label
    >
  </div>
  <div class="graph-breadcrumb">
    <button onclick={() => navigate([])}>{payload.document.name}</button
    >{#each path as key, index}<span>›</span><button
        onclick={() => navigate(path.slice(0, index + 1))}>{key}</button
      >{/each}<span class="graph-note">{message || ui.no_execute}</span>
  </div>
  <div
    class="graph-body"
    class:hide-menu={!menu}
    style:--canvas-height={`min(${payload.config.limits.canvas_height}px, max(${payload.config.limits.canvas_min_height}px, calc(100dvh - ${payload.config.limits.canvas_viewport_offset}px)))`}
  >
    {#if menu}<aside class="graph-palette">
        <h4>{ui.add}</h4>
        {#each Object.entries(payload.config.groups).filter( ([key]) => ["filter", "factor", "scorer", "ensemble", "agent"].includes(key) ) as [kind, group]}
          <details open>
            <summary>{group.label}</summary
            >{#each Object.entries(payload.schema.components).filter(([, spec]) => spec.kind === kind) as [key, spec]}<button
                draggable="true"
                ondragstart={(event) =>
                  event.dataTransfer?.setData(
                    "application/aiquant-component",
                    key,
                  )}
                title={payload.config.help[kind]}
                disabled={Boolean(plan.sleeves?.length)}
                onclick={() =>
                  edit(() => {
                    selected = addStage(plan, payload, key).id;
                  })}><i style:background={group.color}></i>{spec.label}</button
              >{/each}
          </details>
        {/each}
      </aside>{/if}
    <div
      class="graph-canvas"
      bind:this={canvas}
      role="region"
      aria-label={ui.title}
      ondrop={drop}
      ondragover={(event) => event.preventDefault()}
    >
      <SvelteFlow
        bind:nodes
        bind:edges
        {nodeTypes}
        fitView
        minZoom={Number(payload.config.limits.min_zoom)}
        maxZoom={Number(payload.config.limits.max_zoom)}
        deleteKey={null}
        isValidConnection={(c) => canConnect(plan, payload, c)}
        onconnect={connectNodes}
        onnodeclick={({ node, event }) => {
          select(node.id, false);
          if (event instanceof MouseEvent && event.detail === 2) enter();
        }}
        onedgeclick={({ edge }) => {
          selectedEdge = edge.data?.protected ? "" : edge.id;
        }}
        onnodedragstop={() => capture()}
      >
        <Background /><Controls /><MiniMap
          pannable
          zoomable
          nodeColor={(node) => String(node.data.color || "#64748b")}
        />
      </SvelteFlow>
      {#if selectedEdge}<button
          class="remove-edge"
          onclick={() => {
            const edge = edges.find((e) => e.id === selectedEdge);
            if (edge) edit(() => disconnect(plan, edge.source, edge.target));
            selectedEdge = "";
          }}>{ui.delete_edge}</button
        >{/if}
      {#if payload.issues.length}<div class="graph-issues" role="alert">
          {payload.issues.join("\n")}
        </div>{/if}
      {#if payload.evidence.error}<div class="graph-issues" role="alert">
          {payload.evidence.error}
        </div>{/if}
    </div>
    <Properties
      {payload}
      {path}
      {selected}
      onselect={select}
      onupdate={updateNode}
      onremove={remove}
      onduplicate={duplicate}
      onoutput={() => edit(() => (plan.output = selected))}
      onenter={enter}
      onbudget={(value) =>
        edit(() => {
          const sleeve = plan.sleeves?.find((s) => "s:" + s.id === selected);
          if (sleeve) sleeve.budget = value;
        })}
    />
  </div>
  <div class="graph-footer">
    <span class:graph-warning={Boolean(stale)}
      >{stale ? ui.stale : dirty ? ui.modified : ui.clean}</span
    >{#if payload.evidence.run_id}<span
        >{payload.evidence.run_id} · {payload.evidence.status}</span
      >{/if}<span>Alt+← / Alt+→ · Esc · Ctrl+Z</span>
  </div>
</div>
