// Formes des réponses de l'API consommées par plusieurs écrans.

/** Enveloppe de toutes les listes paginées (`GET /accounts`, `GET /auth/events`…). */
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/** Un admin tel qu'affiché à côté de ce qu'il a fait ; `is_me` est résolu côté serveur. */
export interface AdminRef {
  id: number;
  display_name: string | null;
  email: string;
  is_me: boolean;
}

/** Un compte admin de la liste `GET /accounts`. */
export interface Account {
  id: number;
  email: string;
  display_name: string | null;
  is_active: boolean;
  has_password: boolean;
  is_me: boolean;
  created_at: string;
  last_login_at: string | null;
}

/** Une ligne du journal d'authentification admin (table `admin_auth_event`). */
export interface AuthEvent {
  id: number;
  occurred_at: string;
  kind: string;
  email: string | null;
  admin_id: number | null;
  ip: string | null;
  user_agent: string | null;
  detail: string | null;
}

// --- Boîte de réception admin ------------------------------------------------

export interface NotificationItem {
  id: number;
  // Clé courte posée par le package émetteur (« item_created »…) ; cf. NOTIFICATION_KINDS.
  kind: string;
  // Null quand l'acteur n'est pas un admin (tâche système, utilisateur final).
  actor: AdminRef | null;
  target_type: string | null;
  target_id: number | null;
  title: string | null;
  preview: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  // Toujours le compteur global du destinataire — il ne bouge pas quand la page se filtre.
  unread: number;
}
