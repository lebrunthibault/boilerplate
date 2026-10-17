<template>
  <header
    class="relative z-10 flex h-28 items-center gap-3 border-b border-app-border bg-app-bg-elevated px-8 py-2"
  >
    <div
      class="pointer-events-none absolute bottom-[-1px] left-0 right-0 h-px opacity-30"
      style="
        background: linear-gradient(
          90deg,
          transparent,
          var(--color-app-accent) 20%,
          var(--color-app-accent) 80%,
          transparent
        );
      "
    />

    <RouterLink to="/" class="flex items-center gap-3">
      <img src="/favicon.svg" alt="" class="h-11 w-auto" />
      <span
        class="font-mono text-2xl font-medium uppercase tracking-[0.08em] text-app-text"
      >
        Boiler<span class="text-app-accent">plate</span>
      </span>
    </RouterLink>

    <nav class="ml-auto flex items-center gap-7">
      <RouterLink
        to="/confidentialite"
        class="font-mono text-sm uppercase tracking-[0.06em] text-app-text-subtle transition-colors hover:text-app-accent"
      >
        Confidentialité
      </RouterLink>
    </nav>
  </header>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>
