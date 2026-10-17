<template>
  <span><template v-for="(seg, i) in segments" :key="i"><a
        v-if="seg.href"
        :href="seg.href"
        target="_blank"
        rel="noopener noreferrer"
        class="text-app-accent hover:underline"
        @click.stop
      >{{ seg.text }}</a><template v-else>{{ seg.text }}</template></template></span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { linkify } from "@/composables/linkify";

const props = defineProps<{ text: string }>();

const segments = computed(() => linkify(props.text));
</script>
