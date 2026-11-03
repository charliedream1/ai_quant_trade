<script lang="ts">
  type RecordValue = Record<string, unknown>;
  let {
    evidence,
    labels,
    date = "",
  }: {
    evidence?: RecordValue;
    labels: Record<string, string>;
    date?: string;
  } = $props();
  const detail = $derived((evidence?.factor_research || {}) as RecordValue);
  const research = $derived((detail.research || {}) as RecordValue);
  const metrics = $derived(
    (research.metrics || {}) as Record<string, RecordValue>,
  );
  const excluded = $derived(
    (research.excluded || {}) as Record<string, string>,
  );
  const selected = $derived(
    (research.selected || detail.factors || []) as string[],
  );
  const observations = $derived(
    (detail.observations || {}) as Record<string, RecordValue>,
  );
  const weights = $derived(
    (Object.values(observations)[0]?.factor_weights || {}) as Record<
      string,
      number
    >,
  );
  const display = (value: unknown) =>
    typeof value === "number" && Number.isFinite(value)
      ? value.toFixed(3)
      : "—";
</script>

{#if detail.as_of && (!date || date === detail.as_of)}
  <section class="factor-evidence" aria-label={labels.factor_evidence}>
    <strong>{labels.factor_evidence} · {String(detail.as_of)}</strong>
    {#if detail.set}<p>{labels.set_name}: {String(detail.set)}</p>{/if}
    {#if detail.computed !== undefined}
      <p>
        {labels.cache_computed}: {String(detail.computed)} · {labels.cache_hits}:
        {String(detail.cache_hits || 0)} · {labels.memory_hits}: {String(
          detail.memory_hits || 0,
        )}
      </p>
    {/if}
    {#if Object.keys(metrics).length}
      <p title={labels.matured_hint}>
        {labels.label_end}: {String(research.label_end || "—")}
      </p>
      <table>
        <thead
          ><tr
            ><th>{labels.factor_name}</th><th title={labels.rank_ic_hint}
              >RankIC</th
            ><th title={labels.icir_hint}>ICIR</th><th>{labels.samples}</th></tr
          ></thead
        >
        <tbody
          >{#each Object.entries(metrics) as [key, metric]}
            <tr
              class:excluded={!selected.includes(key)}
              title={excluded[key] || labels.factor_selected}
            >
              <th>{labels[key] || key}{selected.includes(key) ? " ✓" : ""}</th>
              <td>{display(metric.rank_ic_mean)}</td><td
                >{display(metric.icir)}</td
              ><td>{String(metric.samples)}</td>
            </tr>
          {/each}</tbody
        >
      </table>
      {#each Object.entries(excluded) as [key, reason]}<small
          >{labels[key] || key}: {labels[reason] || reason}</small
        >{/each}
    {/if}
    {#if Object.keys(weights).length}
      <p title={labels.factor_weights_hint}>{labels.factor_weights}</p>
      {#each Object.entries(weights) as [key, weight]}
        <div class="factor-weight">
          <span>{labels[key] || key}</span><progress
            max="1"
            value={weight}
            aria-label={labels[key] || key}
          ></progress><span>{(weight * 100).toFixed(1)}%</span>
        </div>
      {/each}
    {/if}
  </section>
{/if}

<style>
  .factor-evidence {
    margin: 12px 0;
    padding: 12px;
    border: 1px solid var(--graph-line, #dbe5ed);
    border-radius: 12px;
    background: color-mix(in srgb, #0891b2 7%, transparent);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  th,
  td {
    padding: 6px 3px;
    text-align: right;
    border-bottom: 1px solid #94a3b833;
  }
  th:first-child {
    text-align: left;
    font-weight: 500;
  }
  .excluded {
    opacity: 0.6;
  }
  small {
    display: block;
    margin-top: 5px;
    overflow-wrap: anywhere;
  }
  .factor-weight {
    display: grid;
    grid-template-columns: 1fr 1fr 44px;
    align-items: center;
    gap: 6px;
    margin: 6px 0;
    font-size: 12px;
  }
  progress {
    width: 100%;
    height: 7px;
    accent-color: #0891b2;
  }
</style>
