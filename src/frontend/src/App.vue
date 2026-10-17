<template>
  <AppHeader v-if="!route.path.startsWith('/admin')" />
  <div v-if="!route.path.startsWith('/admin')" class="container mx-auto px-4">
    <router-view />
  </div>
  <router-view v-else />
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";
import AppHeader from "@/components/AppHeader.vue";

const route = useRoute();
</script>
