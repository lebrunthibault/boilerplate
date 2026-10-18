<template>
  <div class="flex flex-1 flex-col">
    <!-- Title bar -->
    <div class="flex items-center border-b border-app-border px-5 py-3.5 lg:px-8">
      <h1 class="text-sm font-medium text-app-text">Appels LLM</h1>
    </div>

    <!-- Top bar -->
    <div class="border-b border-app-border bg-app-bg-elevated px-8 py-5">
      <div class="flex items-center gap-4">
        <select v-model="task" class="field w-64 text-sm" @change="onFilterChange">
          <option value="">Toutes les tâches</option>
          <option v-for="name in tasks" :key="name" :value="name">{{ name }}</option>
        </select>
        <label class="flex items-center gap-2 text-sm text-app-text-muted">
          <input v-model="errorsOnly" type="checkbox" @change="onFilterChange" />
          Échecs seulement
        </label>
        <span class="ml-auto text-sm text-app-text-subtle">
          {{ total }} appel{{ total !== 1 ? "s" : "" }}
        </span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex flex-1 items-center justify-center text-sm text-app-text-subtle">
      Chargement...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="p-8">
      <div class="callout callout--danger">{{ error }}</div>
    </div>

    <!-- Empty -->
    <div
      v-else-if="items.length === 0"
      class="flex flex-1 items-center justify-center text-sm text-app-text-subtle"
    >
      Aucun appel journalisé
    </div>

    <!-- Table -->
    <div v-else class="flex flex-1 flex-col">
      <div class="flex-1 overflow-auto">
        <table class="w-full">
          <thead class="sticky top-0 z-10">
            <tr class="border-b border-app-border bg-app-bg-elevated">
              <th v-for="col in COLUMNS" :key="col.label" :class="col.class">{{ col.label }}</th>
            </tr>
          </thead>
          <tbody>
            <LlmCallRow v-for="item in items" :key="item.id" :call="item" />
          </tbody>
        </table>
      </div>

      <PaginationBar :page="page" :pages="pages" @update:page="onPageChange" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PaginationBar from "@/components/PaginationBar.vue";
import { useAuth } from "@/composables/useAuth";
import { usePaginatedList } from "@/composables/usePaginatedList";
import type { LlmCallSummary } from "@/types";
import LlmCallRow from "./LlmCallRow.vue";

const TH = "py-3 text-[11px] font-medium uppercase tracking-wider text-app-text-subtle";
const COLUMNS = [
  { label: "Date", class: `px-8 text-left ${TH}` },
  { label: "Tâche", class: `px-6 text-left ${TH}` },
  { label: "Modèle", class: `px-6 text-left ${TH}` },
  { label: "Cible", class: `px-6 text-left ${TH}` },
  { label: "Tokens in / out", class: `px-6 text-right ${TH}` },
  { label: "Coût", class: `px-6 text-right ${TH}` },
  { label: "Durée", class: `px-6 text-right ${TH}` },
];

const route = useRoute();
const router = useRouter();
const { authFetch } = useAuth();
const task = ref("");
const errorsOnly = ref(false);
const tasks = ref<string[]>([]);
const { items, page, pages, total, isLoading, error, fetchPage } =
  usePaginatedList<LlmCallSummary>("/api/llm-calls", 50);

function currentQuery(p = 1): Record<string, string> {
  const query: Record<string, string> = {};
  if (p > 1) query.page = String(p);
  if (task.value) query.task = task.value;
  if (errorsOnly.value) query.errors_only = "true";
  return query;
}

function onPageChange(p: number) {
  router.push({ query: currentQuery(p) });
}

function onFilterChange() {
  // Un changement de filtre repart de la première page.
  router.push({ query: currentQuery() });
}

function syncFromRoute() {
  task.value = (route.query.task as string) || "";
  errorsOnly.value = route.query.errors_only === "true";
  const p = parseInt(route.query.page as string, 10);
  fetchPage(p > 0 ? p : 1, { task: task.value, errors_only: errorsOnly.value ? "true" : "" });
}

async function loadTasks() {
  const res = await authFetch("/api/llm-calls/tasks");
  if (res.ok) tasks.value = await res.json();
}

watch(() => route.query, syncFromRoute);
onMounted(() => {
  syncFromRoute();
  loadTasks();
});
</script>
