import { ref } from "vue";
import type { Paginated } from "@/types";
import { useAuth } from "@/composables/useAuth";

/**
 * Liste paginée générique : un endpoint qui rend `Paginated<T>`, des paramètres de requête en
 * plus de `page` / `per_page`. Chaque écran de liste (comptes, journal…) s'appuie dessus.
 */
export function usePaginatedList<T>(url: string, perPage = 25) {
  const { authFetch } = useAuth();
  const items = ref<T[]>([]);
  const page = ref(1);
  const pages = ref(0);
  const total = ref(0);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchPage(p: number = 1, extra: Record<string, string> = {}) {
    isLoading.value = true;
    error.value = null;
    try {
      const params = new URLSearchParams({ page: String(p), per_page: String(perPage) });
      for (const [key, value] of Object.entries(extra)) if (value) params.set(key, value);
      const res = await authFetch(`${url}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Paginated<T> = await res.json();
      items.value = data.items as typeof items.value;
      page.value = data.page;
      pages.value = data.pages;
      total.value = data.total;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Erreur inconnue";
    } finally {
      isLoading.value = false;
    }
  }

  return { items, page, pages, total, isLoading, error, fetchPage };
}
