import { createRouter, createWebHistory } from "vue-router";
import { revalidateSession, sessionIsAlive } from "@/composables/useAuth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      component: () => import("@/pages/LoginPage.vue"),
    },
    {
      path: "/confidentialite",
      component: () => import("@/pages/ConfidentialitePage.vue"),
    },
    {
      path: "/",
      component: () => import("@/pages/LandingPage.vue"),
    },
    {
      path: "/admin",
      component: () => import("@/pages/admin/AdminLayout.vue"),
      children: [
        {
          path: "",
          redirect: "/admin/accounts",
        },
        {
          path: "accounts",
          component: () => import("@/pages/admin/AdminAccountsPage.vue"),
        },
        {
          path: "inbox",
          component: () => import("@/pages/admin/inbox/Index.vue"),
        },
        {
          path: "securite",
          component: () => import("@/pages/admin/AdminSecurityPage.vue"),
        },
        {
          path: "llm",
          component: () => import("@/pages/admin/llm/Index.vue"),
        },
        // Route derrière un feature flag (cf. config/features.ts) :
        // { path: "example", component: …, beforeEnter: () => (features.example ? true : { path: "/admin" }) },
      ],
    },
  ],
});

const PUBLIC_PATHS = new Set(["/", "/login", "/confidentialite"]);

router.beforeEach(async (to) => {
  if (PUBLIC_PATHS.has(to.path)) return;
  if (sessionIsAlive()) return;
  if (await revalidateSession()) return;
  return { path: "/login", query: { redirect: to.fullPath } };
});

export default router;
