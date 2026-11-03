import type { Node } from "@xyflow/svelte";

export type Stage = {
  id: string;
  component: string;
  inputs?: string[];
  params?: Record<string, unknown>;
  family?: string;
};
export type Definition = {
  name: string;
  nodes?: Stage[];
  output?: string;
  universe?: { symbols: string[] };
  sleeves?: Sleeve[];
  portfolio?: { component: string; params?: Record<string, unknown> };
  risk?: Record<string, unknown>;
  execution?: Record<string, unknown>;
  [key: string]: unknown;
};
export type Sleeve = { id: string; budget: number; definition: Definition };
export type CanvasLayout = {
  positions?: Record<string, { x: number; y: number }>;
  viewport?: { x: number; y: number; zoom: number };
  selected?: string;
};
export type Evidence = {
  run_id?: string;
  status?: string;
  definition_digest?: string;
  error?: string;
  dates?: string[];
  nodes?: Record<
    string,
    {
      stages: Record<string, unknown>[];
      events: Record<string, unknown>[];
      [key: string]: unknown;
    }
  >;
};
export type Payload = {
  doc_id: string;
  edit_revision: number;
  layout_session: string;
  layout_origin: string;
  update_sequences?: Record<string, string>;
  applied_revision?: number;
  document: Definition;
  base_digest: string;
  compiled_digest: string;
  layout_key: string;
  layout_revision: number;
  layout: Record<string, CanvasLayout>;
  issues: string[];
  evidence: Evidence;
  read_only: boolean;
  schema: {
    components: Record<
      string,
      { kind: string; label: string; defaults: Record<string, unknown> }
    >;
    portfolios: Record<string, string>;
    defaults: Record<string, Record<string, unknown>>;
    max_nodes: number;
    max_depth: number;
  };
  config: {
    ui: Record<string, string>;
    help: Record<string, string>;
    labels: Record<string, string>;
    choices: Record<string, string[]>;
    groups: Record<string, { label: string; color: string }>;
    ports: Record<string, { input: string; output: string }>;
    parameter_limits: Record<
      string,
      { min?: number; max?: number; step?: number }
    >;
    status_labels?: Record<string, string>;
    limits: Record<string, number | string>;
  };
};
export type GraphPatch = {
  kind:
    "load" | "sync" | "applied" | "issues" | "binding" | "layout" | "evidence";
  doc_id: string;
  edit_revision: number;
  sequence: string;
  payload?: Payload;
  evidence?: Evidence;
  issues?: string[];
  layout_key?: string;
  layout_session?: string;
  layout_revision?: number;
  layout?: Record<string, CanvasLayout>;
};
export type GraphData = {
  label: string;
  component: string;
  kind: string;
  kindLabel: string;
  inputType: string;
  outputType: string;
  summary: string;
  color: string;
  protected: boolean;
  status: string;
  selected: boolean;
  context?: boolean;
};
export type VisualNode = Node<GraphData>;
export type Send = (
  kind: "apply" | "layout" | "draft",
  payload: Payload,
) => void;
