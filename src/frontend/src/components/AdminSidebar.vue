<template>
  <aside class="flex flex-col border-r border-app-border bg-app-bg-elevated px-3 py-5">
    <router-link to="/admin" class="mb-7 flex items-center gap-2 px-2">
      <span class="sidebar-mark">B</span>
      <span class="font-mono text-xs uppercase tracking-[0.08em]">Boiler<b class="font-[inherit] text-app-accent">plate</b></span>
      <span class="ml-auto text-[10px] text-app-text-subtle">v{{ version }}</span>
    </router-link>

    <nav class="flex flex-col gap-0.5">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ 'nav-item--active': route.path.startsWith(item.to) }"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="ICONS[item.icon]" />
        {{ item.label }}
        <span v-if="item.to === '/admin/inbox' && unread" class="count">{{ unread > 99 ? "99+" : unread }}</span>
      </router-link>
    </nav>

    <div class="mt-auto border-t border-app-border pt-4 relative">
      <button @click="showSettings = !showSettings" class="nav-item w-full">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="ICONS.settings" />
      </button>
      <div v-if="showSettings" class="absolute bottom-full left-0 z-10 mb-1 w-full flex flex-col gap-0.5 rounded-md border border-app-border bg-app-bg-elevated p-1 shadow-lg">
        <button @click="logout" class="nav-item w-full">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="ICONS.logout" />
          Déconnexion
        </button>
      </div>
      <Teleport to="body">
        <div v-if="showSettings" class="fixed inset-0" @click="showSettings = false" />
      </Teleport>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute } from "vue-router";
import { useAuth } from "@/composables/useAuth";
import { useNotifications } from "@/composables/useNotifications";

const route = useRoute();
const showSettings = ref(false);
const { logout } = useAuth();
const { unread } = useNotifications();

const version = import.meta.env.VITE_APP_VERSION;

// Tracés SVG 24×24 (style Feather/Lucide), injectés dans un <svg> commun.
const ICONS = {
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>',
  users: '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>',
  logout: '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>',
};

// Une entrée par écran admin ; un écran derrière un feature flag filtre ici (cf. features.ts).
const navItems: { to: string; label: string; icon: keyof typeof ICONS }[] = [
  { to: "/admin/inbox", label: "Réception", icon: "inbox" },
  { to: "/admin/accounts", label: "Comptes", icon: "users" },
  { to: "/admin/securite", label: "Sécurité", icon: "shield" },
  { to: "/admin/llm", label: "Appels LLM", icon: "cpu" },
];
</script>

<style scoped>
.sidebar-mark {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--color-app-accent), oklch(0.55 0.12 250));
  display: grid;
  place-items: center;
  color: var(--color-app-bg);
  font-weight: 700;
  font-size: 13px;
}
</style>
