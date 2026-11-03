<script lang="ts">
  import type { Payload, Definition } from "./types";
  import { fields, scopeKey } from "./documents";
  import FactorEvidence from "./FactorEvidence.svelte";
  type Props = {
    payload: Payload;
    path: string[];
    selected: string;
    onselect: (id: string) => void;
    onupdate: (params: Record<string, unknown>, method: string) => void;
    onremove: () => void;
    onduplicate: () => void;
    onoutput: () => void;
    onenter: () => void;
    onbudget: (v: number) => void;
  };
  let {
    payload,
    path,
    selected,
    onselect,
    onupdate,
    onremove,
    onduplicate,
    onoutput,
    onenter,
    onbudget,
  }: Props = $props();
  const ui = $derived(payload.config.ui);
  const plan = $derived(
    path.reduce(
      (p: Definition, key) => p.sleeves!.find((s) => s.id === key)!.definition,
      payload.document,
    ),
  );
  const node = $derived(plan.nodes?.find((n) => n.id === selected));
  const sourceParameters = $derived(
    JSON.stringify(fields(payload, plan, selected)),
  );
  const sourceMethod = $derived(plan.portfolio?.component || "equal");
  let form = $state<Record<string, unknown>>({}),
    advanced = $state(""),
    method = $state("equal"),
    error = $state("");
  const nodeEvidence = $derived(
    payload.evidence.nodes?.[scopeKey(path) + "/" + selected],
  );
  let date = $state("");
  let panel: HTMLElement;
  $effect(() => {
    selected;
    scopeKey(path);
    date = "";
    if (panel) panel.scrollTop = 0;
  });
  $effect(() => {
    selected;
    const next = JSON.parse(sourceParameters);
    form = next;
    advanced = JSON.stringify(next, null, 2);
    method = sourceMethod;
    error = "";
  });
  const parents = $derived(node?.inputs || []);
  const children = $derived(
    (plan.nodes || [])
      .filter((n) => (n.inputs || []).includes(selected))
      .map((n) => n.id),
  );
  const scalar = $derived(
    Object.entries(form).filter(
      ([key, value]) =>
        ["number", "boolean", "string"].includes(typeof value) &&
        !["backend", "title"].includes(key),
    ),
  );
  function apply(json = false) {
    try {
      const params = json ? JSON.parse(advanced) : form;
      if (!params || Array.isArray(params) || typeof params !== "object")
        throw new Error("Parameters must be an object");
      onupdate(params, method);
    } catch (e) {
      error = String(e);
    }
  }
</script>

<aside class="graph-properties" bind:this={panel}>
  <div class="property-heading">
    <span>{ui.parameters}</span><strong>{selected || ui.choose}</strong>
  </div>
  {#if selected}
    {#if selected.startsWith("s:")}
      <button class="graph-primary" onclick={onenter}>{ui.enter}</button>
      <label
        >{ui.budget}<input
          type="number"
          min="0"
          max="1"
          step="0.05"
          value={plan.sleeves?.find((s) => "s:" + s.id === selected)?.budget}
          onchange={(e) => onbudget(Number(e.currentTarget.value))}
        /></label
      >
    {:else if selected === "universe"}
      <p>{payload.config.help.universe}</p>
      <div class="graph-code">
        {plan.universe?.symbols?.join(", ") || ui.context}
      </div>
    {:else}
      <p>
        {(node && payload.config.help[node.component]) ||
          payload.config.help[
            node
              ? payload.schema.components[node.component]?.kind
              : selected.slice(1)
          ] ||
          ""}
      </p>
      {#if selected === "@portfolio"}<label
          >{ui.portfolio}<select bind:value={method}
            >{#each Object.entries(payload.schema.portfolios) as [key, label]}<option
                value={key}>{label}</option
              >{/each}</select
          ></label
        >{/if}
      <div class="property-fields">
        {#each scalar as [key, value]}
          <label title={key}
            >{(node && payload.config.labels[node.component + "." + key]) ||
              payload.config.labels[key] ||
              key}
            {#if typeof value === "boolean"}<input
                type="checkbox"
                checked={Boolean(form[key])}
                onchange={(e) =>
                  (form = { ...form, [key]: e.currentTarget.checked })}
              />
            {:else if payload.config.choices[key]}<select
                value={String(form[key])}
                onchange={(e) =>
                  (form = { ...form, [key]: e.currentTarget.value })}
                >{#each payload.config.choices[key] as option}<option
                    >{option}</option
                  >{/each}</select
              >
            {:else}<input
                type={typeof value === "number" ? "number" : "text"}
                value={String(form[key])}
                min={payload.config.parameter_limits[key]?.min}
                max={payload.config.parameter_limits[key]?.max}
                step={payload.config.parameter_limits[key]?.step || "any"}
                oninput={(e) =>
                  (form = {
                    ...form,
                    [key]:
                      typeof value === "number"
                        ? Number(e.currentTarget.value)
                        : e.currentTarget.value,
                  })}
              />{/if}
          </label>
        {/each}
      </div>
      <button class="graph-primary" onclick={() => apply()}>{ui.update}</button>
      <details>
        <summary>{ui.advanced}</summary><textarea
          aria-label={ui.advanced}
          bind:value={advanced}
          rows="9"></textarea><button onclick={() => apply(true)}
          >{ui.update}</button
        >
      </details>
      {#if node}<div class="node-actions">
          <button onclick={onduplicate}>{ui.duplicate}</button><button
            onclick={onoutput}>{ui.output}</button
          ><button class="danger" onclick={onremove}>{ui.remove}</button>
        </div>{:else}<small>{ui.protected}</small>{/if}
    {/if}
    {#if error}<p role="alert" class="graph-error">{error}</p>{/if}
    <section class="relationships">
      <h4>{ui.parents}</h4>
      {#each parents as id}<button onclick={() => onselect(id)}>{id} ↖</button
        >{/each}
      <h4>{ui.children}</h4>
      {#each children as id}<button onclick={() => onselect(id)}>{id} ↗</button
        >{/each}
    </section>
    <details open class="node-evidence">
      <summary>{ui.evidence}</summary>
      {#if payload.evidence.run_id}
        <small>{payload.evidence.run_id} · {payload.evidence.status}</small>
        {#if payload.compiled_digest !== payload.evidence.definition_digest}<p
            class="graph-warning"
          >
            {ui.stale}
          </p>{/if}
        <label
          >{ui.date}<select bind:value={date}
            ><option value="">—</option
            >{#each [...new Set(nodeEvidence?.stages.map( (s) => String(s.as_of) ) || [])] as day}<option
                >{day}</option
              >{/each}</select
          ></label
        >
        <FactorEvidence
          evidence={nodeEvidence}
          labels={payload.config.labels}
          {date}
        />
        <pre>{JSON.stringify(
            nodeEvidence
              ? {
                  ...nodeEvidence,
                  stages: nodeEvidence.stages.filter(
                    (s) => !date || s.as_of === date,
                  ),
                  events: nodeEvidence.events.filter(
                    (e) =>
                      !date ||
                      (e.data as Record<string, unknown>)?.as_of === date,
                  ),
                }
              : { message: ui.empty },
            null,
            2,
          )}</pre>
      {:else}<p>{ui.empty}</p>{/if}
    </details>
  {/if}
</aside>
