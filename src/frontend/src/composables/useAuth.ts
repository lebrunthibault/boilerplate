import { computed } from "vue";
import { useRouter, type Router } from "vue-router";

// Le cookie de session est httponly : le SPA ne peut ni le lire ni voir son échéance. On stocke
// donc l'échéance renvoyée par l'API (epoch ms) pour renvoyer vers /login dès qu'elle est passée,
// au lieu de la découvrir sur un appel API qui échoue au milieu d'un écran d'admin.
const STORAGE_KEY = "app_auth";

// Échéance inconnue (API plus ancienne que le bundle, réponse illisible) : on considère la session
// valide quelques minutes, puis on revalide via /api/auth/me. Le 401 d'authFetch reste le filet.
const UNKNOWN_EXPIRY_GRACE_MS = 5 * 60 * 1000;

function rememberSession(expiresAt: unknown) {
  const parsed = typeof expiresAt === "string" ? Date.parse(expiresAt) : NaN;
  const deadline = Number.isNaN(parsed) ? Date.now() + UNKNOWN_EXPIRY_GRACE_MS : parsed;
  sessionStorage.setItem(STORAGE_KEY, String(deadline));
}

export function forgetSession() {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function sessionIsAlive(): boolean {
  const deadline = Number(sessionStorage.getItem(STORAGE_KEY));
  return deadline > Date.now();
}

/** Vérifie le cookie auprès de l'API et mémorise l'échéance. Hors composant (garde de routage). */
export async function revalidateSession(): Promise<boolean> {
  try {
    const resp = await fetch("/api/auth/me");
    if (!resp.ok) {
      forgetSession();
      return false;
    }
    rememberSession((await resp.json()).expires_at);
    return true;
  } catch {
    return false; // erreur réseau — on retombe sur le login
  }
}

function redirectToLogin(router: Router) {
  const current = router.currentRoute.value;
  if (current.path === "/login") return;
  router.push({ path: "/login", query: { redirect: current.fullPath } });
}

export function useAuth() {
  const router = useRouter();

  const isAuthenticated = computed(() => sessionIsAlive());

  /** Statut HTTP de la tentative (200, 401, 429…) — le composant choisit le message. */
  async function login(email: string, password: string): Promise<number> {
    const resp = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (resp.ok) {
      rememberSession((await resp.json()).expires_at);
    }
    return resp.status;
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    forgetSession();
    router.push("/login");
  }

  async function authFetch(
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> {
    const resp = await fetch(input, init);
    if (resp.status !== 401) return resp;

    forgetSession();
    redirectToLogin(router);
    // Session morte : on ne rend jamais la 401 à l'appelant, sinon chaque écran affiche son
    // « HTTP 401 » (ou plante sur res.json()) le temps que la navigation vers /login se fasse.
    // La promesse reste pendante ; le composant est démonté par la redirection.
    return new Promise<Response>(() => {});
  }

  return { isAuthenticated, login, logout, authFetch };
}
