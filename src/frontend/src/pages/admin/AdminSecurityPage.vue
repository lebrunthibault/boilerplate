<template>
  <div class="flex flex-1 flex-col">
    <!-- Title bar -->
    <div class="flex items-center border-b border-app-border px-5 py-3.5 lg:px-8">
      <h1 class="text-sm font-medium text-app-text">Sécurité</h1>
    </div>

    <!-- Top bar -->
    <div class="border-b border-app-border bg-app-bg-elevated px-8 py-5">
      <div class="flex items-center justify-between gap-4">
        <select v-model="kind" class="field w-64 text-sm" @change="onKindChange">
          <option value="">Tous les événements</option>
          <option v-for="option in KINDS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <span class="text-sm text-app-text-subtle">
          {{ total }} événement{{ total !== 1 ? "s" : "" }}
        </span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex flex-1 items-center justify-center text-sm text-app-text-subtle">
      Chargement...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="p-8">
      <div class="rounded-lg border border-app-danger bg-app-danger-soft px-5 py-4 text-sm text-app-danger">
        {{ error }}
      </div>
    </div>

    <!-- Empty -->
    <div
      v-else-if="items.length === 0"
      class="flex flex-1 items-center justify-center text-sm text-app-text-subtle"
    >
      Aucun événement
    </div>

    <!-- Table -->
    <div v-else class="flex flex-1 flex-col">
      <div class="flex-1 overflow-auto">
        <table class="w-full">
          <thead class="sticky top-0 z-10">
            <tr class="border-b border-app-border bg-app-bg-elevated">
              <th class="px-8 py-3 text-left text-[11px] font-medium uppercase tracking-wider text-app-text-subtle">
                Date
              </th>
              <th class="px-6 py-3 text-left text-[11px] font-medium uppercase tracking-wider text-app-text-subtle">
                Événement
              </th>
              <th class="px-6 py-3 text-left text-[11px] font-medium uppercase tracking-wider text-app-text-subtle">
                Compte
              </th>
              <th class="px-6 py-3 text-left text-[11px] font-medium uppercase tracking-wider text-app-text-subtle">
                IP
              </th>
              <th class="px-6 py-3 text-left text-[11px] font-medium uppercase tracking-wider text-app-text-subtle">
                Navigateur
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id" class="border-b border-app-border">
              <td class="whitespace-nowrap px-8 py-4 text-xs text-app-text-subtle">
                {{ formatDateTime(item.occurred_at, true) }}
              </td>
              <td class="px-6 py-4">
                <span class="tag" :class="toneOf(item.kind)">{{ labelOf(item.kind) }}</span>
                <span v-if="item.detail" class="ml-2 text-xs text-app-text-subtle">
                  {{ item.detail }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-app-text">
                {{ item.email || "—" }}
                <!-- Une adresse sans compte = tentative sur une adresse inconnue. -->
                <span v-if="item.email && item.admin_id === null" class="ml-1 text-xs text-app-text-subtle">
                  (compte inconnu)
                </span>
              </td>
              <td class="px-6 py-4 font-mono text-xs text-app-text-muted">
                {{ item.ip || "—" }}
              </td>
              <td class="max-w-xs truncate px-6 py-4 text-xs text-app-text-subtle" :title="item.user_agent || ''">
                {{ item.user_agent || "—" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <PaginationBar :page="page" :pages="pages" @update:page="onPageChange" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePaginatedList } from "@/composables/usePaginatedList";
import { formatDateTime } from "@/format";
import type { AuthEvent } from "@/types";
import PaginationBar from "@/components/PaginationBar.vue";

const KINDS = [
  { value: "login_success", label: "Connexion", tone: "tag--green" },
  { value: "login_failure", label: "Échec de connexion", tone: "tag--danger" },
  { value: "login_blocked", label: "Blocage (trop d'essais)", tone: "tag--gold" },
  { value: "logout", label: "Déconnexion", tone: "tag--muted" },
  { value: "sessions_revoked", label: "Sessions révoquées", tone: "tag--gold" },
  { value: "step_up_success", label: "Confirmation acceptée", tone: "tag--green" },
  { value: "step_up_failure", label: "Confirmation refusée", tone: "tag--danger" },
];

const route = useRoute();
const router = useRouter();
const kind = ref("");
const { items, page, pages, total, isLoading, error, fetchPage } = usePaginatedList<AuthEvent>(
  "/api/auth/events",
  50,
);

function labelOf(value: string) {
  return KINDS.find((k) => k.value === value)?.label ?? value;
}

function toneOf(value: string) {
  return KINDS.find((k) => k.value === value)?.tone ?? "tag--muted";
}

function onPageChange(p: number) {
  const query: Record<string, string> = {};
  if (p > 1) query.page = String(p);
  if (kind.value) query.kind = kind.value;
  router.push({ query });
}

function onKindChange() {
  // Un changement de filtre repart de la première page : la pagination ne survit pas au filtre.
  router.push({ query: kind.value ? { kind: kind.value } : {} });
}

function syncFromRoute() {
  kind.value = (route.query.kind as string) || "";
  const p = parseInt(route.query.page as string, 10);
  fetchPage(p > 0 ? p : 1, { kind: kind.value });
}

watch(() => route.query, syncFromRoute);
onMounted(syncFromRoute);

</script>
