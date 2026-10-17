<template>
  <div class="grid h-full" style="grid-template-columns: 220px 1fr">
    <AdminSidebar />
    <main class="flex min-h-0 flex-col overflow-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import AdminSidebar from "@/components/AdminSidebar.vue";
import { useNotifications } from "@/composables/useNotifications";

// Le poll de la pastille vit ici : ce layout n'est monté que sous /admin, donc jamais sur
// /login. L'arrêt à l'`onUnmounted` (déconnexion) évite qu'il continue de tirer des 401 —
// `authFetch` ne résout jamais sa promesse sur 401 — et lui permet de repartir au re-login.
const { startPolling, stopPolling } = useNotifications();
onMounted(startPolling);
onUnmounted(stopPolling);
</script>
