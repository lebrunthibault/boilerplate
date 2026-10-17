<template>
  <div class="flex min-h-screen items-center justify-center">
    <form
      class="w-full max-w-sm rounded-lg border border-app-border bg-app-bg-elevated p-8"
      @submit.prevent="handleLogin"
    >
      <h1 class="mb-6 text-center text-2xl font-semibold text-app-text">
        Boilerplate
      </h1>

      <div v-if="error" class="mb-4 rounded border border-app-danger/30 bg-app-danger-soft px-3 py-2 text-sm text-app-danger">
        {{ error }}
      </div>

      <label class="mb-1 block text-sm text-app-text-muted">Email</label>
      <input
        v-model="email"
        type="email"
        autocomplete="username"
        class="mb-4 w-full rounded border border-app-border bg-app-bg-sunken px-3 py-2 text-app-text outline-none focus:border-app-border-focus"
      />

      <label class="mb-1 block text-sm text-app-text-muted">Mot de passe</label>
      <input
        v-model="password"
        type="password"
        autocomplete="current-password"
        class="mb-6 w-full rounded border border-app-border bg-app-bg-sunken px-3 py-2 text-app-text outline-none focus:border-app-border-focus"
      />

      <button
        type="submit"
        :disabled="isLoading"
        class="w-full rounded bg-app-accent px-4 py-2 font-medium text-white transition hover:brightness-110 disabled:opacity-50"
      >
        {{ isLoading ? "Connexion..." : "Se connecter" }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuth } from "@/composables/useAuth";

const route = useRoute();
const router = useRouter();
const { login } = useAuth();

const email = ref("");
const password = ref("");
const isLoading = ref(false);
const error = ref<string | null>(null);

async function handleLogin() {
  isLoading.value = true;
  error.value = null;

  try {
    const httpStatus = await login(email.value, password.value);
    if (httpStatus === 429) {
      error.value = "Trop de tentatives, réessayez dans quelques minutes";
      return;
    }
    if (httpStatus !== 200) {
      error.value = "Identifiants incorrects";
      return;
    }
    const redirect = route.query.redirect;
    router.push(typeof redirect === "string" ? redirect : "/admin");
  } catch {
    error.value = "Impossible de contacter le serveur";
  } finally {
    isLoading.value = false;
  }
}
</script>
