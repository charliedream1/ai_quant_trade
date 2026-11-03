import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mergeGraphUpdate } from "../src/updates.ts";
import type { Payload, GraphPatch } from "../src/types.ts";

const source = JSON.parse(
  readFileSync(new URL("./payload.json", import.meta.url), "utf8"),
);
const fresh = (): Payload => ({
  ...structuredClone(source),
  doc_id: "first",
  edit_revision: 0,
  layout_session: "session",
  layout_origin: "rule_trend",
});
const patch = (
  kind: GraphPatch["kind"],
  extra: Partial<GraphPatch> = {},
): GraphPatch => ({
  kind,
  doc_id: "first",
  edit_revision: 0,
  sequence: "1",
  ...extra,
});

test("evidence never replaces an edited document or layout, and old-document evidence is rejected", () => {
  const current = fresh();
  current.document.risk = { max_exposure: 0.5 };
  current.edit_revision = 1;
  current.layout.main = { positions: { trend: { x: 123, y: 90 } } };
  const next = mergeGraphUpdate(
    current,
    patch("evidence", { payload: fresh(), evidence: { run_id: "real-run" } }),
    true,
  );
  assert.deepEqual(next.value.document, current.document);
  assert.deepEqual(next.value.layout, current.layout);
  assert.equal(next.dirty, true);
  assert.equal(next.value.evidence.run_id, "real-run");
  assert.equal(
    mergeGraphUpdate(next.value, patch("evidence", { doc_id: "older" }), true)
      .accepted,
    false,
  );
});

test("reloading an identical preset resets pending edits and prevents older callbacks from restoring them", () => {
  const current = fresh(),
    loaded = fresh();
  current.document.risk = { max_exposure: 0.3 };
  current.edit_revision = 2;
  loaded.doc_id = "second";
  loaded.layout = {};
  const next = mergeGraphUpdate(
    current,
    patch("load", { edit_revision: 2, payload: loaded }),
    true,
  );
  assert.equal(next.reset, true);
  assert.equal(next.dirty, false);
  assert.equal(next.value.doc_id, "second");
  assert.deepEqual(next.value.document, loaded.document);
  assert.equal(
    mergeGraphUpdate(
      next.value,
      patch("sync", { sequence: "9", payload: current }),
      false,
    ).accepted,
    false,
  );
});

test("newer YAML and evidence responses survive reversed completion order", () => {
  const current = fresh(),
    later = fresh();
  later.document.name = "later YAML";
  const next = mergeGraphUpdate(
    current,
    patch("sync", { sequence: "2", payload: later }),
    false,
  );
  assert.equal(
    mergeGraphUpdate(next.value, patch("sync", { payload: fresh() }), false)
      .accepted,
    false,
  );
  const run = mergeGraphUpdate(
    next.value,
    patch("evidence", { sequence: "4", evidence: { run_id: "new" } }),
    false,
  );
  assert.equal(
    mergeGraphUpdate(
      run.value,
      patch("evidence", { sequence: "3", evidence: { run_id: "old" } }),
      false,
    ).accepted,
    false,
  );
});

test("explicit load completes even if the old draft was edited while the request was pending", () => {
  const current = fresh(),
    loaded = fresh();
  current.edit_revision = 2;
  loaded.doc_id = "loaded";
  const next = mergeGraphUpdate(
    current,
    patch("load", { edit_revision: 1, payload: loaded }),
    true,
  );
  assert.equal(next.accepted, true);
  assert.equal(next.value.doc_id, "loaded");
  assert.equal(next.value.edit_revision, 0);
  assert.equal(next.dirty, false);
});

test("an earlier apply acknowledgement preserves newer typing and advances only the YAML base", () => {
  const current = fresh(),
    applied = fresh();
  current.edit_revision = 2;
  current.document.risk = { max_exposure: 0.4 };
  applied.base_digest = "new-yaml-base";
  const next = mergeGraphUpdate(
    current,
    patch("applied", { edit_revision: 1, payload: applied }),
    true,
  );
  assert.deepEqual(next.value.document.risk, { max_exposure: 0.4 });
  assert.equal(next.value.base_digest, "new-yaml-base");
  assert.equal(next.dirty, true);
  assert.equal(
    mergeGraphUpdate(
      current,
      patch("issues", { edit_revision: 1, issues: ["obsolete"] }),
      true,
    ).accepted,
    false,
  );
});

test("layout acknowledgements preserve newer drag coordinates and reject another layout identity", () => {
  const current = fresh();
  current.layout_key = "draft:current";
  current.layout.main = { positions: { trend: { x: 5, y: 6 } } };
  const next = mergeGraphUpdate(
    current,
    patch("layout", {
      layout_key: current.layout_key,
      layout_revision: 3,
      layout: {},
    }),
    true,
  );
  assert.deepEqual(next.value.layout.main.positions?.trend, { x: 5, y: 6 });
  assert.equal(next.value.layout_revision, 3);
  assert.equal(
    mergeGraphUpdate(
      current,
      patch("layout", { layout_key: "draft:other" }),
      true,
    ).accepted,
    false,
  );
});
