<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 grid place-items-center bg-black/50" @click.self="emit('cancel')">
      <form class="card w-full max-w-sm" @submit.prevent="emit('confirm', password)">
        <div class="card__head">
          <span class="card__title">{{ title }}</span>
        </div>
        <div class="card__body flex flex-col gap-3">
          <p class="text-app-text-muted">{{ description }}</p>
          <label class="text-xs text-app-text-subtle" for="step-up-password">
            Confirmez avec votre mot de passe
          </label>
          <input
            id="step-up-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            class="field"
            autofocus
          />
          <div v-if="error" class="callout callout--danger">{{ error }}</div>
          <div class="flex justify-end gap-2">
            <button type="button" class="btn btn--ghost" @click="emit('cancel')">Annuler</button>
            <button type="submit" class="btn btn--danger" :disabled="!password">
              {{ confirmLabel }}
            </button>
          </div>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from "vue";

// Ré-authentification avant un acte destructeur (step-up) : le parent appelle l'API avec le
// mot de passe et repasse l'erreur éventuelle (403 = mot de passe faux, 429 = bloqué).
defineProps<{ title: string; description: string; confirmLabel: string; error: string | null }>();
const emit = defineEmits<{ confirm: [password: string]; cancel: [] }>();

const password = ref("");
</script>
