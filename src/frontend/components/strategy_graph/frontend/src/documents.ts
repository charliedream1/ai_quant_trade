import type { Edge, Connection } from "@xyflow/svelte";
import type {
  Definition,
  Payload,
  VisualNode,
  Stage,
  GraphData,
} from "./types";

export const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value));
export const scopeKey = (path: string[]) => ["main", ...path].join("/");
export function scoped(document: Definition, path: string[]): Definition {
  return path.reduce((value, key) => {
    const child = value.sleeves?.find((s) => s.id === key);
    if (!child) throw new Error("Unknown graph scope");
    return child.definition;
  }, document);
}

export function fields(
  payload: Payload,
  plan: Definition,
  id: string,
): Record<string, unknown> {
  if (id === "@portfolio")
    return { ...payload.schema.defaults.portfolio, ...plan.portfolio?.params };
  if (id === "@risk") return { ...payload.schema.defaults.risk, ...plan.risk };
  if (id === "@execution")
    return { ...payload.schema.defaults.execution, ...plan.execution };
  const node = plan.nodes?.find((n) => n.id === id);
  return node
    ? { ...payload.schema.components[node.component]?.defaults, ...node.params }
    : {};
}

export function graph(
  payload: Payload,
  path: string[],
): { nodes: VisualNode[]; edges: Edge[] } {
  const plan = scoped(payload.document, path),
    cfg = payload.config,
    key = scopeKey(path);
  const positions = payload.layout[key]?.positions || {};
  const levels: Record<string, number> = { universe: 0 };
  const stages = plan.nodes || [],
    pending = [...stages];
  for (let pass = 0; pass <= stages.length && pending.length; pass++)
    for (const stage of [...pending]) {
      if ((stage.inputs || ["universe"]).every((p) => p in levels)) {
        levels[stage.id] =
          1 + Math.max(...(stage.inputs || ["universe"]).map((p) => levels[p]));
        pending.splice(pending.indexOf(stage), 1);
      }
    }
  const edges: Edge[] = [],
    nodes: VisualNode[] = [],
    row: Record<number, number> = {};
  const add = (id: string, data: GraphData, level: number) => {
    const y = row[level] || 0;
    row[level] = y + 1;
    const record =
      payload.compiled_digest &&
      payload.compiled_digest === payload.evidence.definition_digest
        ? payload.evidence.nodes?.[key + "/" + id]
        : undefined;
    const last = record?.stages.at(-1);
    const latest = record?.events.findLast((event) => event.kind === "stage")
      ?.data as Record<string, unknown> | undefined;
    const rawStatus = String(latest?.status || last?.status || "");
    const status = cfg.status_labels?.[rawStatus] || rawStatus;
    if (last?.passed !== undefined)
      data.summary = `${cfg.ui.passed} ${last.passed} / ${last.input_count} · ${last.duration_ms} ${cfg.ui.milliseconds}`;
    nodes.push({
      id,
      type: "strategy",
      position: positions[id] || {
        x: level * Number(cfg.limits.layout_gap_x),
        y: y * Number(cfg.limits.layout_gap_y),
      },
      data: { ...data, status, selected: false },
      deletable: !data.protected,
    });
  };
  const data = (
    label: string,
    component: string,
    kind: string,
    summary: string,
    locked = false,
  ): GraphData => ({
    label,
    component,
    kind,
    kindLabel: cfg.groups[kind]?.label || kind,
    inputType: cfg.ports[kind]?.input || "",
    outputType: cfg.ports[kind]?.output || "",
    summary,
    color: cfg.groups[kind]?.color || cfg.groups.context.color,
    protected: locked,
    status: "",
    selected: false,
  });
  const edge = (
    source: string,
    target: string,
    label = "",
    locked = false,
    context = false,
  ) =>
    edges.push({
      id: source + ">" + target + (context ? ":context" : ""),
      source,
      target,
      label,
      selectable: !locked,
      deletable: !locked,
      style: context ? "stroke-dasharray:4 5;opacity:.45" : undefined,
      data: { protected: locked, context },
      markerEnd: { type: "arrowclosed" as never },
    });
  add(
    "universe",
    data(
      cfg.ui.universe,
      "context",
      "context",
      String(plan.universe?.symbols?.length || 0),
      true,
    ),
    0,
  );
  for (const node of stages) {
    const spec = payload.schema.components[node.component];
    add(
      node.id,
      data(
        node.id,
        spec?.label || node.component,
        spec?.kind || "context",
        (node.inputs || ["universe"]).join(", "),
      ),
      levels[node.id] ?? 1,
    );
    for (const parent of node.inputs || ["universe"]) edge(parent, node.id);
    if (
      ["lightgbm", "xgboost", "mlp"].includes(node.component) &&
      !(node.inputs || []).includes("universe")
    )
      edge("universe", node.id, cfg.ui.context, true, true);
  }
  for (const sleeve of plan.sleeves || []) {
    add(
      "s:" + sleeve.id,
      data(
        sleeve.id,
        sleeve.definition.name,
        "portfolio",
        cfg.ui.budget + " " + (sleeve.budget * 100).toFixed(1) + "%",
        true,
      ),
      1,
    );
    edge("universe", "s:" + sleeve.id, "", true);
  }
  const end =
    1 + Math.max(0, ...Object.values(levels), plan.sleeves?.length ? 1 : 0);
  add(
    "@portfolio",
    data(
      cfg.ui.portfolio,
      payload.schema.portfolios[plan.portfolio?.component || "equal"],
      "portfolio",
      cfg.ui.protected,
      true,
    ),
    end,
  );
  if (plan.sleeves?.length)
    for (const sleeve of plan.sleeves)
      edge(
        "s:" + sleeve.id,
        "@portfolio",
        (sleeve.budget * 100).toFixed(1) + "%",
        true,
      );
  else edge(plan.output || "universe", "@portfolio", "", true);
  add(
    "@risk",
    data(cfg.ui.risk, "risk", "risk", cfg.ui.protected, true),
    end + 1,
  );
  add(
    "@execution",
    data(cfg.ui.execution, "execution", "context", cfg.ui.protected, true),
    end + 2,
  );
  edge("@portfolio", "@risk", "", true);
  edge("@risk", "@execution", "", true);
  return { nodes, edges };
}

export function canConnect(
  plan: Definition,
  payload: Payload,
  connection: Pick<Connection, "source" | "target">,
): boolean {
  const { source, target } = connection;
  if (
    !source ||
    !target ||
    source === target ||
    source.startsWith("@") ||
    target.startsWith("@") ||
    source.startsWith("s:") ||
    target.startsWith("s:")
  )
    return false;
  const node = plan.nodes?.find((n) => n.id === target);
  const sourceNode = plan.nodes?.find((n) => n.id === source);
  if (
    !node ||
    (source !== "universe" && !sourceNode) ||
    sourceNode?.component === "agent" ||
    (node.inputs || []).includes(source)
  )
    return false;
  const kind = payload.schema.components[node.component]?.kind;
  const sourceKind = sourceNode
    ? payload.schema.components[sourceNode.component]?.kind
    : "filter";
  const needsPanel = [
    "factor_preprocess",
    "factor_select",
    "factor_score",
  ].includes(node.component);
  if (needsPanel !== (sourceKind === "factor")) return false;
  if (
    node.component === "factor_preprocess" &&
    sourceNode?.component === "factor_select"
  )
    return false;
  if (
    node.component === "factor_score" &&
    node.params?.weighting === "icir" &&
    sourceNode?.component !== "factor_select"
  )
    return false;
  if (kind !== "ensemble" && (node.inputs || []).length) return false;
  const visit = (id: string, seen: Set<string>): boolean => {
    if (id === target) return true;
    if (seen.has(id)) return false;
    seen.add(id);
    return (plan.nodes?.find((n) => n.id === id)?.inputs || []).some((p) =>
      visit(p, seen),
    );
  };
  return !visit(source, new Set());
}

export function connect(
  plan: Definition,
  payload: Payload,
  connection: Connection,
): boolean {
  if (!canConnect(plan, payload, connection)) return false;
  const target = plan.nodes!.find((n) => n.id === connection.target)!;
  target.inputs = [...(target.inputs || []), connection.source];
  const weights = target.params?.weights;
  if (Array.isArray(weights) && weights.length)
    target.params!.weights = [...weights, 1];
  return true;
}

export function disconnect(plan: Definition, source: string, target: string) {
  const stage = plan.nodes?.find((n) => n.id === target);
  if (!stage) return;
  const index = (stage.inputs || []).indexOf(source);
  if (index < 0) return;
  stage.inputs = stage.inputs!.filter((_, i) => i !== index);
  if (Array.isArray(stage.params?.weights) && stage.params.weights.length)
    stage.params.weights = stage.params.weights.filter((_, i) => i !== index);
}

export function newId(plan: Definition, stem: string) {
  let id = stem,
    index = 1;
  while (plan.nodes?.some((n) => n.id === id)) id = stem + "_" + index++;
  return id;
}

export function addStage(
  plan: Definition,
  payload: Payload,
  component: string,
): Stage {
  if (
    plan.sleeves?.length ||
    !payload.schema.components[component] ||
    (plan.nodes?.length || 0) >= payload.schema.max_nodes
  )
    throw new Error("Component unavailable in this scope");
  const node = {
    id: newId(plan, component),
    component,
    inputs: ["universe"],
    params: {},
  };
  if (
    ["factor_preprocess", "factor_select", "factor_score"].includes(component)
  ) {
    const parent = [...(plan.nodes || [])]
      .reverse()
      .find(
        (stage) =>
          payload.schema.components[stage.component]?.kind === "factor" &&
          !(
            component === "factor_preprocess" &&
            stage.component === "factor_select"
          ),
      );
    node.inputs = parent ? [parent.id] : [];
  }
  (plan.nodes ??= []).push(node);
  return node;
}
