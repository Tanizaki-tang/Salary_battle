<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch"></div>
      <div class="status-bar dark">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>
      <div class="call-active-bg">
        <div class="call-avatar-large">🏁</div>
        <div class="call-name">谈判结算</div>
        <div class="call-role">Session {{ sessionId }}</div>
        <div class="call-company">劳资拉扯模拟器</div>

        <div v-if="result" class="result-card">
          <div class="row"><span>总分</span><strong>{{ result.final_score }}</strong></div>
          <div class="row"><span>最终薪资</span><strong>{{ salaryText }}</strong></div>
          <div class="row"><span>评级</span><strong>{{ result.grade }}</strong></div>
          <div class="tip">{{ result.review_tip }}</div>
        </div>

        <div v-else class="result-card">正在结算...</div>

        <div class="call-actions">
          <button class="call-btn call-btn-mute" @click="$router.push('/')">↺</button>
          <button class="call-btn call-btn-hangup" @click="loadResult" :disabled="loading">
            {{ loading ? "…" : "⟳" }}
          </button>
          <button class="call-btn call-btn-mute" @click="$router.push('/')">⌂</button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { runtimeAdapter } from "../runtime";

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));
const loading = ref(false);
const error = ref("");
const result = ref<{ final_score: number; final_salary: number; grade: string; review_tip: string } | null>(null);

async function loadResult() {
  loading.value = true;
  error.value = "";
  try {
    const data = await runtimeAdapter.settle(sessionId.value);
    result.value = data.result;
    sessionStorage.removeItem("currentSession");
    sessionStorage.removeItem("hrOpening");
  } catch (e) {
    error.value = `结算失败：${String(e)}`;
  } finally {
    loading.value = false;
  }
}

const salaryText = computed(() => {
  if (!result.value) return "-";
  return `${Math.round(result.value.final_salary / 1000)}K`;
});

if (!sessionId.value) {
  router.push("/");
} else {
  void loadResult();
}
</script>

<style scoped>
.page-root { width: 375px; height: 700px; }
.phone-shell { width: 100%; height: 100%; border-radius: 32px; overflow: hidden; position: relative; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a; background: #fff; }
.phone-notch { position: absolute; top: 8px; left: 50%; transform: translateX(-50%); width: 100px; height: 24px; background: #1a1a1a; border-radius: 0 0 16px 16px; z-index: 10; }
.status-bar { height: 36px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0; }
.status-bar.dark { background: #1a1a2e; }
.call-active-bg {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 24px;
  color: #fff;
}
.call-avatar-large {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  margin-top: 20px;
}
.call-name { font-size: 20px; font-weight: 600; margin-top: 12px; }
.call-role { color: rgba(255,255,255,0.7); font-size: 12px; margin-top: 2px; }
.call-company { color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 1px; }
.result-card {
  width: 100%;
  max-width: 310px;
  margin-top: 22px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(255,255,255,0.12);
}
.row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
.row strong { font-size: 16px; }
.tip { margin-top: 10px; font-size: 12px; line-height: 1.6; color: rgba(255,255,255,0.9); }
.call-actions {
  margin-top: auto;
  padding: 16px 0 24px;
  display: flex;
  justify-content: center;
  gap: 36px;
}
.call-btn {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  font-size: 22px;
  color: #fff;
}
.call-btn-hangup { background: #ff4757; }
.call-btn-mute {
  width: 48px;
  height: 48px;
  font-size: 18px;
  background: rgba(255,255,255,0.15);
}
.error { color: #ff9aa2; font-size: 12px; }
</style>
