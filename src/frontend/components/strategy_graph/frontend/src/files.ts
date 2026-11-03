import type { Payload, Definition } from "./types";

export function downloadDocument(payload: Payload) {
  const data = JSON.stringify(
    {
      format: "aiquant-strategy-graph",
      version: 1,
      document: payload.document,
      layout: payload.layout,
    },
    null,
    2,
  );
  const url = URL.createObjectURL(
    new Blob([data], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "strategy-graph.json";
  link.click();
  URL.revokeObjectURL(url);
}

export async function readDocument(file: File, payload: Payload) {
  if (file.size > Number(payload.config.limits.max_bytes))
    throw new Error(payload.config.ui.invalid_file);
  const value = JSON.parse(await file.text());
  if (
    value.format !== "aiquant-strategy-graph" ||
    value.version !== 1 ||
    typeof value.document?.name !== "string"
  )
    throw new Error(payload.config.ui.invalid_file);
  const check = (doc: Definition, depth: number) => {
    if (
      depth > payload.schema.max_depth ||
      !Array.isArray(doc.nodes ?? []) ||
      (doc.nodes?.length || 0) > payload.schema.max_nodes
    )
      throw new Error(payload.config.ui.invalid_file);
    for (const node of doc.nodes || [])
      if (
        !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(node.id) ||
        !payload.schema.components[node.component] ||
        !Array.isArray(node.inputs ?? [])
      )
        throw new Error(payload.config.ui.invalid_file);
    for (const child of doc.sleeves || []) check(child.definition, depth + 1);
  };
  check(value.document, 0);
  return value;
}
