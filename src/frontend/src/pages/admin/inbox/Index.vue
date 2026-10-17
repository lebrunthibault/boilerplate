<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex items-center justify-between border-b border-app-border px-5 py-3.5 lg:px-8">
      <h1 class="text-sm font-medium text-app-text">
        Boîte de réception
        <span v-if="unread" class="ml-2 font-mono text-xs text-app-text-subtle">
          {{ unread }} non {{ unread > 1 ? "lues" : "lue" }}
        </span>
      </h1>
      <div class="flex items-center gap-2">
        <div class="tabs">
          <button class="tab" :class="{ 'tab--active': !unreadOnly }" @click="setFilter(false)">
            Toutes
          </button>
          <button class="tab" :class="{ 'tab--active': unreadOnly }" @click="setFilter(true)">
            Non lues
          </button>
        </div>
        <button class="btn btn--secondary btn--sm" :disabled="!unread" @click="markAllRead">
          Tout marquer comme lu
        </button>
      </div>
    </div>

    <div v-if="isLoading && !items.length" class="flex flex-1 items-center justify-center text-sm text-app-text-muted">
      Chargement…
    </div>

    <div v-else-if="!visibleItems.length" class="flex flex-1 items-center justify-center text-sm text-app-text-muted">
      {{ unreadOnly ? "Rien de non lu." : "Aucune notification." }}
    </div>

    <div v-else class="min-h-0 flex-1 overflow-auto px-5 py-4 lg:px-8">
      <section v-for="group in groups" :key="group.label" class="mb-6 last:mb-0">
        <h2 class="mb-1.5 px-1 text-xs font-medium text-app-text-muted">{{ group.label }}</h2>
        <div class="card card__body--flush overflow-hidden">
          <NotificationRow
            v-for="item in group.items"
            :key="item.id"
            :item="item"
            @open="open(item)"
            @toggle-read="setRead(item.id, !item.read_at)"
            @remove="remove(item.id)"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import type { NotificationItem } from "@/types";
import { LOCALE } from "@/format";
import { useNotifications } from "@/composables/useNotifications";
import NotificationRow from "./NotificationRow.vue";
import { targetPath } from "./kinds";

const router = useRouter();
const { items, unread, isLoading, fetchNotifications, setRead, markAllRead, remove } =
  useNotifications();

const unreadOnly = ref(false);

onMounted(() => fetchNotifications());

function setFilter(value: boolean) {
  unreadOnly.value = value;
}

// Le filtre est local : la liste chargée porte tout, et une ligne qu'on vient de lire ne
// disparaît pas sous le curseur en mode « non lues ».
const visibleItems = computed(() =>
  unreadOnly.value ? items.value.filter((n) => !n.read_at) : items.value,
);

interface Group {
  label: string;
  items: NotificationItem[];
}

const DAY_MS = 24 * 60 * 60 * 1000;

// Regroupement par ancienneté, façon boîte de réception : le jour même, la semaine, puis
// par mois. Les lignes arrivent déjà triées du plus récent au plus ancien.
function groupLabel(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (date.getTime() >= startOfToday) return "Aujourd'hui";
  if (date.getTime() >= startOfToday - 7 * DAY_MS) return "Les 7 derniers jours";
  const month = date.toLocaleDateString(LOCALE, { month: "long" });
  return date.getFullYear() === now.getFullYear() ? month : `${month} ${date.getFullYear()}`;
}

const groups = computed<Group[]>(() => {
  const out: Group[] = [];
  for (const item of visibleItems.value) {
    const label = groupLabel(item.created_at);
    const last = out[out.length - 1];
    if (last && last.label === label) last.items.push(item);
    else out.push({ label, items: [item] });
  }
  return out;
});

async function open(item: NotificationItem) {
  if (!item.read_at) await setRead(item.id, true);
  const path = targetPath(item);
  if (path) router.push(path);
}
</script>
