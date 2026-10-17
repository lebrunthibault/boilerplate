<template>
  <div class="flex min-h-[calc(100vh-7rem)] flex-col">
    <main class="mx-auto w-full max-w-5xl flex-1 px-5 sm:px-8">
      <!-- Hero -->
      <section class="flex flex-col items-center py-24 text-center sm:py-32">
        <h1
          class="mb-6 font-mono text-5xl font-medium uppercase tracking-[0.08em] text-app-text sm:text-6xl"
        >
          [Nom du produit]
        </h1>
        <p
          class="mb-8 inline-block rounded-full border border-app-accent-line px-4 py-1.5 font-mono text-sm uppercase tracking-[0.12em] text-app-accent"
        >
          [Secteur / cible]
        </p>
        <p class="mb-5 max-w-3xl text-xl leading-relaxed text-app-text">
          [Promesse en une phrase : quel problème vous résolvez, pour qui.]
        </p>
        <p class="mb-10 max-w-2xl text-lg leading-relaxed text-app-text-muted">
          [Deux lignes de contexte : comment le produit s'intègre au quotidien de vos clients.]
        </p>
        <div class="flex flex-wrap items-center justify-center gap-4">
          <a href="mailto:contact@exemple.fr" class="btn btn--primary h-12 px-7 text-base">
            Nous contacter
          </a>
          <RouterLink to="/login" class="btn btn--secondary h-12 px-7 text-base">
            Espace administrateur
          </RouterLink>
        </div>
      </section>

      <!-- Bénéfices -->
      <section class="border-t border-app-border py-20 sm:py-24">
        <div class="mx-auto mb-14 max-w-2xl text-center">
          <p class="mb-4 font-mono text-sm uppercase tracking-[0.15em] text-app-accent">Bénéfices</p>
          <h2 class="text-3xl font-semibold leading-tight text-app-text sm:text-4xl">
            Ce que [Nom du produit] vous apporte
          </h2>
        </div>

        <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <article
            v-for="benefit in benefits"
            :key="benefit.title"
            class="group card flex flex-col p-6 transition duration-200 hover:-translate-y-0.5 hover:border-app-accent-line motion-reduce:transition-none motion-reduce:hover:translate-y-0 sm:p-7"
          >
            <span
              class="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-lg bg-app-accent-soft text-app-accent ring-1 ring-inset ring-app-accent-line transition group-hover:bg-app-accent-line"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="h-[22px] w-[22px]"
                aria-hidden="true"
              >
                <path :d="benefit.icon" />
              </svg>
            </span>
            <h3 class="mb-2.5 text-lg font-semibold text-app-text">{{ benefit.title }}</h3>
            <p class="text-base leading-relaxed text-app-text-muted">{{ benefit.description }}</p>
          </article>
        </div>
      </section>
    </main>

    <footer class="border-t border-app-border py-8 text-center text-sm text-app-text-subtle">
      <RouterLink to="/confidentialite" class="transition-colors hover:text-app-accent">
        Confidentialité
      </RouterLink>
      <span class="mx-2">·</span>
      <span>© {{ year }} [Raison sociale]</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

const year = new Date().getFullYear();

// Trois à six bénéfices ; `icon` est le tracé d'un pictogramme 24×24 (style Feather/Lucide).
const benefits = [
  {
    title: "[Bénéfice 1]",
    description: "[Une ou deux phrases concrètes, côté client.]",
    icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  },
  {
    title: "[Bénéfice 2]",
    description: "[Une ou deux phrases concrètes, côté client.]",
    icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  },
  {
    title: "[Bénéfice 3]",
    description: "[Une ou deux phrases concrètes, côté client.]",
    icon: "M20 6L9 17l-5-5",
  },
];
</script>
