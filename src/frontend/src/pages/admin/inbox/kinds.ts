import type { NotificationItem } from "@/types";

/**
 * Ce que chaque `kind` de notification raconte, et où mène un clic. Un package qui émet un
 * nouveau `kind` côté API (`notify_admins`) l'ajoute ici — sinon la ligne affiche la clé brute.
 */
export const VERBS: Record<string, string> = {
  system_alert: "Alerte système",
  item_created: "a créé",
  item_updated: "a modifié",
};

// Page de détail d'une cible, par `target_type`. Absent = ligne non cliquable.
const TARGET_ROUTES: Record<string, (id: number) => string> = {
  // item: (id) => `/admin/items/${id}`,
};

export function targetPath(item: NotificationItem): string | null {
  if (!item.target_type || item.target_id === null) return null;
  const route = TARGET_ROUTES[item.target_type];
  return route ? route(item.target_id) : null;
}
