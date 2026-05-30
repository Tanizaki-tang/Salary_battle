import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import StartPage from "./pages/StartPage.vue";
import BattlePage from "./pages/BattlePage.vue";
import ResultPage from "./pages/ResultPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: StartPage },
    { path: "/battle/:sessionId", component: BattlePage },
    { path: "/result/:sessionId", component: ResultPage },
  ],
});

createApp(App).use(router).mount("#app");
