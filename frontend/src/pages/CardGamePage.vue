<template>
  <section class="cg-redirect">
    <p>卡牌对局请在对话页全屏展开后进行。</p>
    <router-link to="/" class="cg-link">返回首页</router-link>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

onMounted(() => {
  router.replace("/");
});
</script>

<style scoped>
.cg-redirect {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  background: #0a1628;
  color: rgba(255, 255, 255, 0.85);
}
.cg-link { color: #7bed9f; }
</style>
