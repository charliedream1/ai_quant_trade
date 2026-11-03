<script lang="ts">
  import { SvelteFlowProvider } from "@xyflow/svelte";
  import Editor from "./Editor.svelte";
  import type { Payload, Send, GraphPatch } from "./types";
  let { initial, send }: { initial: Payload; send: Send } = $props();
  let editor: Editor;
  export function update(value: GraphPatch) {
    editor?.update(value);
  }
</script>

<SvelteFlowProvider
  ><Editor {initial} {send} bind:this={editor} /></SvelteFlowProvider
>
