<template>
  <div class="flex flex-1 flex-col">
    <!-- Title bar -->
    <div class="flex items-center border-b border-app-border px-5 py-3.5 lg:px-8">
      <h1 class="text-sm font-medium text-app-text">Comptes</h1>
      <span class="ml-auto text-sm text-app-text-subtle">
        {{ total }} compte{{ total !== 1 ? "s" : "" }}
      </span>
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
      Aucun compte
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
            <tr v-for="item in items" :key="item.id" class="border-b border-app-border">
              <td class="px-8 py-4 text-sm text-app-text">
                {{ item.email }}
                <span v-if="item.is_me" class="tag tag--accent ml-2">vous</span>
              </td>
              <td class="px-6 py-4 text-sm text-app-text-muted">{{ item.display_name || "—" }}</td>
              <td class="px-6 py-4">
                <span v-if="!item.is_active" class="tag tag--muted">Désactivé</span>
                <span v-else-if="!item.has_password" class="tag tag--gold">Sans mot de passe</span>
                <span v-else class="tag tag--green">Actif</span>
              </td>
              <td class="px-6 py-4 text-right text-xs text-app-text-subtle">
                {{ item.last_login_at ? formatDateTime(item.last_login_at) : "—" }}
              </td>
              <td class="px-6 py-4 text-right">
                <button
                  v-if="item.is_active && !item.is_me"
                  class="btn btn--ghost btn--sm"
                  @click="askDeactivate(item)"
                >
                  Désactiver
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <PaginationBar :page="page" :pages="pages" @update:page="onPageChange" />
    </div>

    <StepUpDialog
      v-if="pending"
      :title="`Désactiver ${pending.email}`"
      description="Le compte ne pourra plus se connecter et ses sessions sont coupées immédiatement."
      confirm-label="Désactiver"
      :error="stepUpError"
      @confirm="deactivate"
      @cancel="pending = null"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PaginationBar from "@/components/PaginationBar.vue";
import StepUpDialog from "@/components/StepUpDialog.vue";
import { useAuth } from "@/composables/useAuth";
import { usePaginatedList } from "@/composables/usePaginatedList";
import { formatDateTime } from "@/format";
import type { Account } from "@/types";

const TH = "py-3 text-[11px] font-medium uppercase tracking-wider text-app-text-subtle";
const COLUMNS = [
  { label: "Email", class: `px-8 text-left ${TH}` },
  { label: "Nom", class: `px-6 text-left ${TH}` },
  { label: "Statut", class: `px-6 text-left ${TH}` },
  { label: "Dernière connexion", class: `px-6 text-right ${TH}` },
  { label: "", class: `px-6 ${TH}` },
];

const route = useRoute();
const router = useRouter();
const { authFetch } = useAuth();
const { items, page, pages, total, isLoading, error, fetchPage } =
  usePaginatedList<Account>("/api/accounts");

const pending = ref<Account | null>(null);
const stepUpError = ref<string | null>(null);

function askDeactivate(account: Account) {
  stepUpError.value = null;
  pending.value = account;
}

async function deactivate(password: string) {
  if (!pending.value) return;
  const res = await authFetch(`/api/accounts/${pending.value.id}/deactivate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmation: { method: "password", password } }),
  });
  if (res.status === 403) {
    stepUpError.value = "Mot de passe incorrect";
    return;
  }
  if (res.status === 429) {
    stepUpError.value = "Trop de tentatives, réessayez dans quelques minutes";
    return;
  }
  if (!res.ok) {
    stepUpError.value = `Erreur HTTP ${res.status}`;
    return;
  }
  pending.value = null;
  syncFromRoute();
}

function onPageChange(p: number) {
  router.push({ query: p > 1 ? { page: String(p) } : {} });
}

function syncFromRoute() {
  const p = parseInt(route.query.page as string, 10);
  fetchPage(p > 0 ? p : 1);
}

watch(() => route.query.page, syncFromRoute);
onMounted(syncFromRoute);
</script>
