<template>
  <div
    class="group flex h-[46px] cursor-pointer select-none items-center gap-3 border-t border-app-border px-5 text-left first:border-t-0 hover:bg-app-bg-hover"
    @click="emit('open')"
  >
    <span class="dot shrink-0" :class="item.read_at ? 'dot--read' : 'dot--accent'" />

    <span
      class="w-[280px] shrink-0 truncate text-app-text"
      :class="{ 'font-semibold': !item.read_at }"
      :title="item.title || undefined"
    >
      {{ item.title || "(sans titre)" }}
    </span>

    <span class="min-w-0 flex-1 truncate text-app-text-muted">
      <b v-if="actorName" class="font-medium text-app-accent">{{ actorName }}</b>
      <span class="ml-1">{{ VERBS[item.kind] ?? item.kind }}</span>
      <span v-if="item.preview" class="ml-2" :class="{ 'font-semibold text-app-text': !item.read_at }">
        {{ item.preview }}
      </span>
    </span>

    <!-- Colonne de droite à largeur fixe : la date au repos, les actions à sa place au survol. -->
    <span class="flex w-32 shrink-0 items-center justify-end">
      <span class="font-mono text-xs text-app-text-subtle group-hover:hidden">
        {{ formatTimeOrDayMonth(item.created_at) }}
      </span>
      <span class="hidden items-center gap-1 group-hover:flex" @click.stop>
        <button
          class="btn btn--ghost btn--sm"
          :title="item.read_at ? 'Marquer comme non lu' : 'Marquer comme lu'"
          @click="emit('toggle-read')"
        >
          {{ item.read_at ? "Non lu" : "Lu" }}
        </button>
        <button class="btn btn--secondary btn--sm" @click="emit('remove')">Effacer</button>
      </span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { NotificationItem } from "@/types";
import { formatTimeOrDayMonth } from "@/format";
import { VERBS } from "./kinds";

const props = defineProps<{ item: NotificationItem }>();
const emit = defineEmits<{ open: []; "toggle-read": []; remove: [] }>();

// Lecture « {nom} {verbe} {aperçu} » ; sans acteur admin (tâche système), le verbe seul.
const actorName = computed(() => {
  const { actor } = props.item;
  return actor ? actor.display_name || actor.email : null;
});
</script>
