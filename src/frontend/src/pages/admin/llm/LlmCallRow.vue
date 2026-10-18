<template>
  <tr class="cursor-pointer border-b border-app-border hover:bg-app-bg-hover" @click="toggle">
    <td class="whitespace-nowrap px-8 py-3 text-xs text-app-text-subtle">
      {{ formatDateTime(call.created_at, true) }}
    </td>
    <td class="px-6 py-3 text-sm text-app-text">
      {{ call.task }}
      <span v-if="call.error" class="tag tag--danger ml-2">échec</span>
    </td>
    <td class="px-6 py-3 font-mono text-xs text-app-text-muted">{{ call.model }}</td>
    <td class="px-6 py-3 text-xs text-app-text-muted">
      {{ call.target_type ? `${call.target_type} #${call.target_id}` : "—" }}
    </td>
    <td class="px-6 py-3 text-right font-mono text-xs text-app-text-muted">
      {{ call.input_tokens ?? "—" }} / {{ call.output_tokens ?? "—" }}
    </td>
    <td class="px-6 py-3 text-right font-mono text-xs text-app-text-muted">
      {{ call.cost_usd !== null ? `$${call.cost_usd.toFixed(4)}` : "—" }}
    </td>
    <td class="px-6 py-3 text-right font-mono text-xs text-app-text-muted">
      {{ formatDuration(call.duration_ms) }}
    </td>
  </tr>
  <tr v-if="open" class="border-b border-app-border bg-app-bg-sunken">
    <td colspan="7" class="px-8 py-5">
      <div v-if="loadError" class="callout callout--danger">{{ loadError }}</div>
      <div v-else-if="!detail" class="text-sm text-app-text-subtle">Chargement...</div>
      <div v-else class="flex flex-col gap-4">
        <div v-if="detail.error" class="callout callout--danger font-mono text-xs">{{ detail.error }}</div>
        <section v-for="block in blocks" :key="block.label">
          <h3 class="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-app-text-subtle">
            {{ block.label }}
          </h3>
          <pre class="max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-md border border-app-border bg-app-bg p-3 font-mono text-xs text-app-text">{{ block.text }}</pre>
        </section>
      </div>
    </td>
  </tr>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useAuth } from "@/composables/useAuth";
import { formatDateTime, formatDuration } from "@/format";
import type { LlmCallDetail, LlmCallSummary } from "@/types";

const props = defineProps<{ call: LlmCallSummary }>();

const { authFetch } = useAuth();
const open = ref(false);
const detail = ref<LlmCallDetail | null>(null);
const loadError = ref<string | null>(null);

// Le détail (prompt, input, output) peut peser lourd : chargé au premier dépliage seulement.
async function toggle() {
  open.value = !open.value;
  if (!open.value || detail.value) return;
  loadError.value = null;
  const res = await authFetch(`/api/llm-calls/${props.call.id}`);
  if (!res.ok) {
    loadError.value = `HTTP ${res.status}`;
    return;
  }
  detail.value = await res.json();
}

const blocks = computed(() => {
  const d = detail.value;
  if (!d) return [];
  const out = [
    { label: "Prompt système", text: d.system_prompt ?? "(introuvable)" },
    { label: "Input", text: d.input },
    { label: "Output", text: typeof d.output === "string" ? d.output : JSON.stringify(d.output, null, 2) },
  ];
  if (d.retries?.length) out.push({ label: "Retries", text: JSON.stringify(d.retries, null, 2) });
  return out;
});
</script>
