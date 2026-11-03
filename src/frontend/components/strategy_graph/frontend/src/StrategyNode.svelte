<script lang="ts">
  import { Handle, Position } from "@xyflow/svelte";
  import type { NodeProps } from "@xyflow/svelte";
  import type { VisualNode } from "./types";
  let { data, selected }: NodeProps<VisualNode> = $props();
</script>

<div
  class:selected
  class="strategy-node"
  style:--node-accent={data.color}
  title={data.summary}
>
  {#if data.kind !== "context" || data.component === "execution"}<Handle
      type="target"
      position={Position.Left}
      title={data.inputType}
      aria-label={data.inputType}
    />{/if}
  <div class="node-top">
    <span class="node-dot"></span><span class="node-kind">{data.kindLabel}</span
    >{#if data.protected}<span aria-label="protected">⌁</span>{/if}
  </div>
  <strong>{data.label}</strong>
  <div class="node-component">{data.component}</div>
  <small>{data.summary}</small>
  {#if data.status}<span class="node-status">{data.status}</span>{/if}
  {#if data.component !== "execution"}<Handle
      type="source"
      position={Position.Right}
      title={data.outputType}
      aria-label={data.outputType}
    />{/if}
</div>
