/**
 * Feature flags front-end — centralisés en un seul endroit.
 *
 * Pilotés par des variables d'env Vite (`VITE_FEATURE_*`). Masqués par défaut :
 * une feature n'est visible que si sa variable vaut exactement la chaîne "true".
 * Pour activer en local, ajouter dans un `.env.local` du dossier frontend :
 *   VITE_FEATURE_EXAMPLE=true
 * En prod, passer la variable en build arg de `docker/Dockerfile.nginx`.
 *
 * Usage côté routeur : `beforeEnter: () => (features.example ? true : { path: "/admin" })`.
 */
export const features = {
  /** Exemple : à remplacer par le premier vrai flag. */
  example: import.meta.env.VITE_FEATURE_EXAMPLE === "true",
} as const;
