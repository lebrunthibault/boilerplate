import "@fontsource-variable/geist";
import "@fontsource-variable/jetbrains-mono";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { installStripCopyBackground } from "./composables/stripCopyBackground";
import "./style.css";

installStripCopyBackground();

createApp(App).use(router).mount("#app");
