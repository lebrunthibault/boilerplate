<template>
  <div v-if="pages > 1" class="flex items-center justify-center border-t border-app-border bg-app-bg-elevated px-8 py-3">
    <nav class="flex items-center gap-1">
      <button
        :disabled="page <= 1"
        class="rounded border border-app-border px-3 py-1.5 text-xs text-app-text-muted transition-colors hover:bg-app-bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
        @click="$emit('update:page', page - 1)"
      >
        &laquo; Précédent
      </button>

      <template v-for="(item, i) in visiblePages" :key="i">
        <span v-if="item === '...'" class="px-1.5 text-xs text-app-text-subtle">&hellip;</span>
        <button
          v-else
          class="min-w-[32px] rounded border px-2 py-1.5 text-xs font-medium transition-colors"
          :class="item === page
            ? 'border-app-accent bg-app-accent text-white'
            : 'border-app-border text-app-text-muted hover:bg-app-bg-hover'"
          @click="$emit('update:page', item)"
        >
          {{ item }}
        </button>
      </template>

      <button
        :disabled="page >= pages"
        class="rounded border border-app-border px-3 py-1.5 text-xs text-app-text-muted transition-colors hover:bg-app-bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
        @click="$emit('update:page', page + 1)"
      >
        Suivant &raquo;
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ page: number; pages: number }>();
defineEmits<{ "update:page": [page: number] }>();

const visiblePages = computed(() => {
  const { page, pages } = props;
  if (pages <= 10) {
    return Array.from({ length: pages }, (_, i) => i + 1);
  }

  const items: (number | "...")[] = [];
  const window = 3;
  const start = Math.max(2, page - window);
  const end = Math.min(pages - 1, page + window);

  items.push(1);
  if (start > 2) items.push("...");
  for (let i = start; i <= end; i++) items.push(i);
  if (end < pages - 1) items.push("...");
  items.push(pages);

  return items;
});
</script>
