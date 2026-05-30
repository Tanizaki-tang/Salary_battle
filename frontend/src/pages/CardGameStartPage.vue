<template>
  <section class="cg-redirect">
    <p>卡牌模式已并入对话页，请先接听电话进入谈判，再点击右上角全屏展开。</p>
    <router-link to="/" class="cg-link">返回首页</router-link>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

onMounted(() => {
  window.setTimeout(() => router.replace("/"), 120);
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
  text-align: center;
}

.cg-link {
  color: #7bed9f;
}
</style>
