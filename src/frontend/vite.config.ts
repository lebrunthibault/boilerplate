import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";
import { existsSync, readFileSync } from "node:fs";

// Version affichée dans la sidebar : lue dans pyproject.toml (source unique). Chemin repo sur
// l'hôte, fichier monté dans /app en docker.
const pyprojectPath = existsSync("../../pyproject.toml") ? "../../pyproject.toml" : "./pyproject.toml";
const pyproject = readFileSync(pyprojectPath, "utf-8");
const versionMatch = pyproject.match(/^version\s*=\s*"(.+)"/m);
process.env.VITE_APP_VERSION = versionMatch ? versionMatch[1] : "0.0.0";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: true,
    proxy: {
      "/api": process.env.API_URL || "http://localhost:8000",
    },
  },
});
