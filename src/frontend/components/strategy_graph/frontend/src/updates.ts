import { copy } from "./documents.ts";
import type { GraphPatch, Payload } from "./types";

/** Server patches update only their own domain; the editable value stays in the browser. */
export function mergeGraphUpdate(
  current: Payload,
  patch: GraphPatch,
  dirty: boolean,
) {
  const unchanged = { value: current, dirty, reset: false, accepted: false };
  if (!patch || patch.doc_id !== current.doc_id) return unchanged;
  const channel = ["load", "sync", "applied", "issues"].includes(patch.kind)
    ? "document"
    : patch.kind;
  const previous = current.update_sequences?.[channel] || "0";
  if (BigInt(patch.sequence) <= BigInt(previous)) return unchanged;
  if (
    !["load", "evidence", "layout", "applied"].includes(patch.kind) &&
    patch.edit_revision !== current.edit_revision
  )
    return unchanged;
  const update_sequences = {
    ...current.update_sequences,
    [channel]: patch.sequence,
  };
  let value = { ...current, update_sequences },
    reset = false;
  if (patch.kind === "load" && patch.payload) {
    value = { ...copy(patch.payload), update_sequences };
    dirty = false;
    reset = true;
  } else if (patch.kind === "sync" && patch.payload) {
    reset =
      JSON.stringify(current.document) !==
      JSON.stringify(patch.payload.document);
    value = { ...copy(patch.payload), update_sequences };
    dirty = false;
  } else if (patch.kind === "applied" && patch.payload) {
    if (patch.edit_revision === current.edit_revision) {
      value = {
        ...copy(patch.payload),
        layout: current.layout,
        update_sequences,
      };
      dirty = false;
    } else {
      // A later local edit survives an acknowledgement of the earlier applied draft.
      value.base_digest = patch.payload.base_digest;
      value.compiled_digest = "";
    }
  } else if (patch.kind === "issues") value.issues = copy(patch.issues || []);
  else if (patch.kind === "evidence")
    value.evidence = copy(patch.evidence || {});
  else if (patch.kind === "layout") {
    if (patch.layout_key !== current.layout_key) return unchanged;
    value.layout_revision = Math.max(
      current.layout_revision,
      patch.layout_revision || 0,
    );
  } else if (patch.kind === "binding") {
    const changed = patch.layout_key !== current.layout_key;
    value.layout_key = patch.layout_key!;
    value.layout_session = patch.layout_session!;
    value.layout_revision = patch.layout_revision || 0;
    if (changed && value.layout_revision)
      value.layout = copy(patch.layout || {});
  } else return unchanged;
  return { value, dirty, reset, accepted: true };
}
