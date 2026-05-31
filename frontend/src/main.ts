import { createApp } from "vue";

import { createRouter, createWebHistory } from "vue-router";

import App from "./App.vue";

import StartPage from "./pages/StartPage.vue";

import BattlePage from "./pages/BattlePage.vue";

import ResultPage from "./pages/ResultPage.vue";

import VoiceBattlePage from "./pages/VoiceBattlePage.vue";

import CardGameStartPage from "./pages/CardGameStartPage.vue";

import CardGamePage from "./pages/CardGamePage.vue";

import CardGameResultPage from "./pages/CardGameResultPage.vue";

import LeaderboardPage from "./pages/LeaderboardPage.vue";



const router = createRouter({

  history: createWebHistory(),

  routes: [

    { path: "/", component: StartPage },

    { path: "/leaderboard", component: LeaderboardPage },

    { path: "/battle/:sessionId", component: BattlePage },

    { path: "/voice-battle/:sessionId", component: VoiceBattlePage },

    { path: "/result/:sessionId", component: ResultPage },

    { path: "/card-game", component: CardGameStartPage },

    { path: "/card-game/play/:sessionId", component: CardGamePage },

    { path: "/card-game/result/:sessionId", component: CardGameResultPage },

  ],

});



createApp(App).use(router).mount("#app");
