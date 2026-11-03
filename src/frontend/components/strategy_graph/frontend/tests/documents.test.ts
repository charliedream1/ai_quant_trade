import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  connect,
  disconnect,
  canConnect,
  graph,
  addStage,
} from "../src/documents.ts";
import type { Payload } from "../src/types.ts";
import { readDocument } from "../src/files.ts";

const fixture = JSON.parse(
  readFileSync(new URL("./payload.json", import.meta.url), "utf8"),
) as Payload;
const fresh = () => JSON.parse(JSON.stringify(fixture)) as Payload;

test("factor panels require typed consumers and new research stages select compatible upstreams", () => {
  const payload = fresh(),
    plan = payload.document;
  payload.schema.components.factor_set = {
    kind: "factor",
    label: "因子集",
    defaults: {},
  };
  payload.schema.components.factor_select = {
    kind: "factor",
    label: "研究",
    defaults: {},
  };
  payload.schema.components.factor_score = {
    kind: "scorer",
    label: "合成",
    defaults: {},
  };
  addStage(plan, payload, "factor_set");
  const research = addStage(plan, payload, "factor_select");
  assert.deepEqual(research.inputs, ["factor_set"]);
  const scores = addStage(plan, payload, "factor_score");
  assert.deepEqual(scores.inputs, ["factor_select"]);
  assert.equal(
    canConnect(plan, payload, { source: "factor_set", target: "rules" }),
    false,
  );
  scores.inputs = [];
  assert.equal(
    canConnect(plan, payload, { source: "universe", target: scores.id }),
    false,
  );
  assert.equal(
    canConnect(plan, payload, { source: "factor_select", target: scores.id }),
    true,
  );
});

test("import accepts the documented format and rejects unknown components and oversized input", async () => {
  const payload = fresh();
  const exported = {
    format: "aiquant-strategy-graph",
    version: 1,
    document: payload.document,
    layout: {},
  };
  const result = await readDocument(
    new File([JSON.stringify(exported)], "graph.json"),
    payload,
  );
  assert.deepEqual(result.document, payload.document);
  exported.document.nodes![0].component = "unregistered_external_code";
  await assert.rejects(
    readDocument(new File([JSON.stringify(exported)], "graph.json"), payload),
  );
  await assert.rejects(
    readDocument(
      new File(
        [" ".repeat(Number(payload.config.limits.max_bytes) + 1)],
        "large.json",
      ),
      payload,
    ),
  );
});

test("actual projected plan includes protected portfolio, risk and execution", () => {
  const payload = fresh();
  const result = graph(payload, []);
  assert(result.nodes.some((n) => n.id === "@risk" && n.data.protected));
  assert(
    result.edges.some((e) => e.source === "@risk" && e.target === "@execution"),
  );
});
test("links reject cycles, agent outputs and protected risk bypass", () => {
  const payload = fresh(),
    plan = payload.document;
  assert.equal(
    canConnect(plan, payload, { source: "rules", target: "trend" }),
    false,
  );
  assert.equal(
    canConnect(plan, payload, { source: "rules", target: "@execution" }),
    false,
  );
  assert.equal(
    canConnect(plan, payload, { source: "trend", target: "rules" }),
    false,
  );
});
test("input removal keeps branch weights attached to the same sources", () => {
  const payload = fresh(),
    plan = payload.document;
  const target = plan.nodes!.find((n) => n.id === "rules")!;
  target.params = { weights: [0.2, 0.3, 0.5] };
  disconnect(plan, "breakout", "rules");
  assert.deepEqual(target.inputs, ["trend", "volume"]);
  assert.deepEqual(target.params.weights, [0.2, 0.5]);
  assert(
    connect(plan, payload, {
      source: "breakout",
      target: "rules",
      sourceHandle: null,
      targetHandle: null,
    }),
  );
  assert.deepEqual(target.params.weights, [0.2, 0.5, 1]);
});
test("layout drag changes positions without changing the calculation document", () => {
  const payload = fresh();
  const before = JSON.stringify(payload.document);
  payload.layout.main = { positions: { trend: { x: 1234, y: 111 } } };
  assert.deepEqual(
    graph(payload, []).nodes.find((n) => n.id === "trend")!.position,
    { x: 1234, y: 111 },
  );
  assert.equal(JSON.stringify(payload.document), before);
});
