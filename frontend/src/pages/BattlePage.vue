<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch"></div>
      <div class="status-bar blue">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>
      <div class="boss-chat">
        <div class="boss-header">
          <div class="boss-header-top">
            <div class="boss-back" @click="$router.push('/')">‹</div>
            <div class="boss-header-name">{{ waitingHr ? "对方正在输入中..." : "张敏 · HR负责人" }}</div>
            <div class="boss-header-actions">⋯</div>
          </div>
        </div>

        <div class="boss-company-card">
          <div class="boss-company-logo">🤖</div>
          <div class="boss-company-info">
            <div class="boss-company-name">{{ session?.scene_context?.meta?.scene_name || "灵创科技" }}</div>
            <div class="boss-company-meta">A轮 · AI/大模型 · 50-100人</div>
          </div>
          <div class="boss-company-salary">{{ salaryText }}</div>
        </div>

        <div class="boss-sat-bar-wrap">
          <div class="boss-sat-label">😊 满意度</div>
          <div class="boss-sat-track">
            <div class="boss-sat-fill" :style="{ width: `${session?.hr_patience ?? 0}%` }"></div>
          </div>
          <div class="boss-sat-val">{{ session?.hr_patience ?? "-" }}</div>
        </div>

        <div class="boss-hud-row">
          <div>🔍 暴露度 <span>{{ session?.info_exposure ?? "-" }}</span></div>
          <div>💰 报价 <span>{{ salaryText }}</span></div>
          <div>🪤 识破 <span>{{ session?.trap_count ?? 0 }}/5</span></div>
        </div>

        <div ref="chatAreaRef" class="boss-chat-area">
          <div class="boss-time-divider">今天 {{ nowTime }}</div>
          <template v-for="(m, idx) in messages" :key="idx">
            <div v-if="m.type === 'system'" class="boss-system-msg">{{ m.text }}</div>
            <div v-else class="boss-msg" :class="m.role === 'hr' ? 'hr' : 'me'">
              <div class="boss-msg-avatar" :class="m.role === 'hr' ? 'hr-avatar' : 'me-avatar'">
                {{ m.role === "hr" ? "👩‍💼" : "🧑" }}
              </div>
              <div class="boss-msg-content">
                <div class="boss-msg-bubble">{{ m.text }}</div>
              </div>
            </div>
          </template>
          <div v-if="waitingHr" class="boss-msg hr">
            <div class="boss-msg-avatar hr-avatar">👩‍💼</div>
            <div class="boss-msg-content">
              <div class="boss-msg-bubble boss-typing-bubble">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <div class="boss-input-area">
          <div class="boss-input-mic">🎤</div>
          <input
            v-model="customText"
            class="boss-input-field"
            placeholder="请输入你的回复（按回车发送）"
            @keydown.enter="sendCustomText"
          />
          <button class="boss-input-send" @click="sendCustomText" :disabled="loading || !customText.trim()">
            {{ loading ? "…" : "↑" }}
          </button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </section>
 </template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { runtimeAdapter } from "../runtime";
import type { SessionState } from "../runtime/battle_runtime_adapter";

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));
const loading = ref(false);
const error = ref("");
const customText = ref("");
const waitingHr = ref(false);
const session = ref<SessionState | null>(null);
const messages = ref<Array<{ role: "hr" | "me" | "system"; text: string; type?: "system" }>>([]);
const chatAreaRef = ref<HTMLElement | null>(null);
const nowTime = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });

const cachedSession = sessionStorage.getItem("currentSession");
if (cachedSession) {
  session.value = JSON.parse(cachedSession) as SessionState;
}
const opening = sessionStorage.getItem("hrOpening");
if (opening) {
  messages.value.push({ role: "hr", text: opening });
}

function scrollChatToBottom() {
  nextTick(() => {
    const el = chatAreaRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

watch(
  () => [messages.value.length, waitingHr.value],
  () => scrollChatToBottom(),
);

onMounted(() => scrollChatToBottom());

async function sendCustomText() {
  await runTurn({ player_text: customText.value.trim() });
  customText.value = "";
}

async function runTurn(payload: { player_text?: string }) {
  const text = payload.player_text?.trim();
  if (text) messages.value.push({ role: "me", text });
  loading.value = true;
  waitingHr.value = true;
  error.value = "";
  try {
    const data = await runtimeAdapter.textTurn(sessionId.value, payload);
    messages.value.push({ role: "hr", text: data.result.hr_reply });
    if (data.flow?.reason) {
      messages.value.push({ role: "system", text: `💡 ${data.flow.reason}`, type: "system" });
    }
    session.value = data.session;
    sessionStorage.setItem("currentSession", JSON.stringify(data.session));
    if (data.flow?.next_phase === "voice") {
      router.push(`/voice/${sessionId.value}`);
      return;
    }
    if (data.flow?.next_phase === "end" || data.result.is_game_over || data.session.status === "settled") {
      router.push(`/result/${sessionId.value}`);
    }
  } catch (e) {
    error.value = `回合请求失败：${String(e)}`;
  } finally {
    waitingHr.value = false;
    loading.value = false;
  }
}

const salaryText = computed(() => {
  const offer = (session.value as any)?.current_salary_offer;
  if (!offer) return "15K";
  return `${Math.round(Number(offer) / 1000)}K`;
});
</script>

<style scoped>
.page-root { width: 375px; height: 700px; }
.phone-shell { width: 100%; height: 100%; border-radius: 32px; overflow: hidden; position: relative; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a; background: #fff; }
.phone-notch { position: absolute; top: 8px; left: 50%; transform: translateX(-50%); width: 100px; height: 24px; background: #1a1a1a; border-radius: 0 0 16px 16px; z-index: 10; }
.status-bar { height: 36px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0; }
.status-bar.blue { background: #00c2a2; }
.boss-chat { background: #f6f6f6; flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.boss-header { background: #00c2a2; padding: 8px 16px 12px; color: #fff; }
.boss-header-top { display: flex; align-items: center; justify-content: space-between; }
.boss-back { font-size: 18px; width: 28px; }
.boss-header-name { font-size: 16px; font-weight: 600; text-align: center; flex: 1; }
.boss-header-actions { width: 28px; text-align: right; }
.boss-company-card { background: #fff; padding: 12px 16px; border-bottom: 1px solid #f0f0f0; display:flex; align-items:center; gap:10px; }
.boss-company-logo { width:40px; height:40px; border-radius:8px; background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; display:flex; align-items:center; justify-content:center; }
.boss-company-info { flex:1; min-width:0; }
.boss-company-name { font-size:14px; font-weight:600; color:#1a1a1a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.boss-company-meta { font-size:11px; color:#999; margin-top:1px; }
.boss-company-salary { font-size:15px; font-weight:700; color:#fa6b3d; }
.boss-sat-bar-wrap { padding:8px 16px; background:#fff; border-bottom:1px solid #f0f0f0; display:flex; align-items:center; gap:8px; }
.boss-sat-label { font-size:11px; color:#666; white-space:nowrap; }
.boss-sat-track { flex:1; height:6px; background:#e8e8e8; border-radius:3px; overflow:hidden; }
.boss-sat-fill { height:100%; background:linear-gradient(90deg,#ff4757,#ffa502,#00c2a2); }
.boss-sat-val { font-size:12px; font-weight:700; color:#333; min-width:24px; text-align:right; }
.boss-hud-row { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); padding:6px 10px; background:#fff; border-bottom:1px solid #f0f0f0; gap:8px; font-size:10px; color:#999; }
.boss-hud-row > div { text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.boss-hud-row span { color:#333; font-weight:600; }
.boss-chat-area { flex:1; min-height:0; overflow-y:auto; overscroll-behavior:contain; padding:12px 16px; display:flex; flex-direction:column; gap:12px; }
.boss-time-divider { text-align:center; font-size:11px; color:#bbb; }
.boss-system-msg { text-align:center; font-size:11px; color:#999; padding:4px 8px; background:rgba(0,0,0,0.03); border-radius:4px; align-self:center; max-width:80%; }
.boss-msg { display:flex; align-items:flex-start; gap:8px; max-width:85%; }
.boss-msg.me { align-self:flex-end; flex-direction:row-reverse; }
.boss-msg.hr { align-self:flex-start; }
.boss-msg-avatar { width:36px; height:36px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:16px; }
.hr-avatar { background:#e8f5e9; }
.me-avatar { background:#e3f2fd; }
.boss-msg-content { display:flex; flex-direction:column; gap:0; min-width:0; }
.boss-msg.me .boss-msg-content { align-items:flex-end; }
.boss-msg-bubble { padding:10px 14px; border-radius:8px; font-size:14px; line-height:1.5; word-break:break-word; overflow-wrap:anywhere; }
.boss-msg.hr .boss-msg-bubble { background:#fff; border-top-left-radius:2px; box-shadow:0 1px 2px rgba(0,0,0,0.04); }
.boss-msg.me .boss-msg-bubble { background:#00c2a2; color:#fff; border-top-right-radius:2px; }
.boss-typing-bubble { display:flex; align-items:center; gap:4px; min-width:42px; }
.boss-typing-bubble span { width:6px; height:6px; border-radius:50%; background:#b7b7b7; animation: dotPulse 1.1s infinite ease-in-out; }
.boss-typing-bubble span:nth-child(2) { animation-delay: 0.15s; }
.boss-typing-bubble span:nth-child(3) { animation-delay: 0.3s; }
@keyframes dotPulse { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
.boss-input-area { padding:8px 12px; background:#f6f6f6; border-top:1px solid #eee; display:flex; gap:8px; align-items:center; }
.boss-input-mic, .boss-input-send { width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; border:none; }
.boss-input-mic { background:#f0f0f0; }
.boss-input-send { background:#00c2a2; color:#fff; }
.boss-input-field { flex:1; height:36px; border:none; background:#fff; border-radius:18px; padding:0 14px; font-size:14px; outline:none; }
.error { margin: 6px 10px 8px; color:#c00; font-size:12px; }
</style>
