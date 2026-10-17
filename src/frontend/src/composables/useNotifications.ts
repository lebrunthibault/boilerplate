import { ref } from "vue";
import type { NotificationItem, NotificationListResponse } from "@/types";
import { useAuth } from "@/composables/useAuth";

// État partagé au niveau module : la pastille de la sidebar et la page /admin/inbox lisent
// le même état, sans prop drilling ni store.
const items = ref<NotificationItem[]>([]);
const unread = ref(0);
const isLoading = ref(false);

// Le poll est démarré une seule fois par AdminLayout ; le drapeau est remis à zéro à
// l'`onUnmounted` (logout) pour qu'il reparte au re-login.
let pollTimer: ReturnType<typeof setInterval> | null = null;
const POLL_INTERVAL_MS = 60_000;

export function useNotifications() {
  const { authFetch } = useAuth();

  async function fetchNotifications(unreadOnly = false) {
    isLoading.value = true;
    try {
      const res = await authFetch(`/api/notifications${unreadOnly ? "?unread_only=true" : ""}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: NotificationListResponse = await res.json();
      items.value = data.items;
      unread.value = data.unread;
    } catch {
      // Silencieux : une boîte de réception qui échoue ne doit pas casser l'écran courant.
    } finally {
      isLoading.value = false;
    }
  }

  /** Rafraîchit le seul compteur (pastille de la sidebar), sans toucher la liste affichée. */
  async function refreshUnread() {
    try {
      const res = await authFetch("/api/notifications?unread_only=true&limit=1");
      if (!res.ok) return;
      unread.value = ((await res.json()) as NotificationListResponse).unread;
    } catch {
      // idem : la pastille garde sa dernière valeur connue.
    }
  }

  async function setRead(id: number, read: boolean) {
    const target = items.value.find((n) => n.id === id);
    if (target && Boolean(target.read_at) === read) return;
    const res = await authFetch(`/api/notifications/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ read }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (target) target.read_at = read ? new Date().toISOString() : null;
    unread.value = Math.max(0, unread.value + (read ? -1 : 1));
  }

  async function markAllRead() {
    const res = await authFetch("/api/notifications/read-all", { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const now = new Date().toISOString();
    items.value.forEach((n) => (n.read_at = n.read_at ?? now));
    unread.value = 0;
  }

  async function remove(id: number) {
    const res = await authFetch(`/api/notifications/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const removed = items.value.find((n) => n.id === id);
    if (removed && !removed.read_at) unread.value = Math.max(0, unread.value - 1);
    items.value = items.value.filter((n) => n.id !== id);
  }

  /** Démarre le poll de la pastille. Idempotent : AdminLayout est le seul appelant. */
  function startPolling() {
    if (pollTimer) return;
    refreshUnread();
    pollTimer = setInterval(() => {
      // Chaque requête admin rafraîchit `last_seen_at` de la session : un onglet laissé en
      // arrière-plan neutraliserait l'expiration par inactivité. On ne tire que visible.
      if (document.visibilityState === "visible") refreshUnread();
    }, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (!pollTimer) return;
    clearInterval(pollTimer);
    pollTimer = null;
  }

  return {
    items, unread, isLoading,
    fetchNotifications, refreshUnread, setRead, markAllRead, remove,
    startPolling, stopPolling,
  };
}
