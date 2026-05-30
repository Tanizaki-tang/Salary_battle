<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch"></div>
      <div class="status-bar dark">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>
      <div class="call-active-bg">
        <div class="call-avatar-large">👩‍💼</div>
        <div class="call-name">张敏</div>
        <div class="call-role">HR负责人</div>
        <div class="call-company">语音协商中</div>
        <div class="call-timer">⏱ {{ timer }}</div>

        <div class="call-hud">
          <div class="call-hud-label">
            <span>😊 HR满意度</span>
            <span>{{ session?.hr_patience ?? "-" }}</span>
          </div>
          <div class="call-hud-bar">
            <div class="call-hud-fill" :style="{ width: `${session?.hr_patience ?? 0}%` }"></div>
          </div>
        </div>

        <div ref="transcriptRef" class="call-transcript">
          <div v-for="(m, idx) in lines" :key="idx" class="call-transcript-line" :class="m.role">
            <div class="call-transcript-bubble">
              <div class="call-transcript-speaker">{{ m.role === "hr" ? "张敏" : "我" }}</div>
              {{ m.text }}
            </div>
          </div>
          <div v-if="waitingHr" class="call-transcript-line hr">
            <div class="call-transcript-bubble call-typing-bubble">
              <div class="call-transcript-speaker">对方正在输入中...</div>
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <div class="voice-input-row">
          <input v-model="voiceText" placeholder="输入你要说的话（模拟语音）" @keydown.enter="sendVoiceRound" />
          <button @click="sendVoiceRound" :disabled="loading || !voiceText.trim()">{{ loading ? "…" : "发送" }}</button>
        </div>

        <div class="call-actions">
          <button class="call-btn call-btn-mute" @click="$router.push(`/battle/${sessionId}`)">💬</button>
          <button class="call-btn call-btn-hangup" @click="$router.push(`/result/${sessionId}`)">📞</button>
          <button class="call-btn call-btn-mute" @click="$router.push('/')">⌂</button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { runtimeAdapter } from "../runtime";
import type { SessionState } from "../runtime/battle_runtime_adapter";

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));
const loading = ref(false);
const error = ref("");
const waitingHr = ref(false);
const voiceText = ref("");
const lines = ref<Array<{ role: "hr" | "me"; text: string }>>([]);
const transcriptRef = ref<HTMLElement | null>(null);
const session = ref<SessionState | null>(null);
const startedAt = Date.now();
const nowTick = ref(Date.now());
const timerHandle = window.setInterval(() => {
  nowTick.value = Date.now();
}, 1000);
onUnmounted(() => {
  window.clearInterval(timerHandle);
});

const cachedSession = sessionStorage.getItem("currentSession");
if (cachedSession) session.value = JSON.parse(cachedSession) as SessionState;
const timer = computed(() => {
  const sec = Math.floor((nowTick.value - startedAt) / 1000);
  const mm = String(Math.floor(sec / 60)).padStart(2, "0");
  const ss = String(sec % 60).padStart(2, "0");
  return `${mm}:${ss}`;
});

function scrollTranscriptToBottom() {
  nextTick(() => {
    const el = transcriptRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

watch(
  () => [lines.value.length, waitingHr.value],
  () => scrollTranscriptToBottom(),
);

function makeDummyWav(text: string): File {
  const bytes = new TextEncoder().encode(`RIFF....WAVE:${text}`);
  return new File([bytes], "voice.wav", { type: "audio/wav" });
}

async function sendVoiceRound() {
  const text = voiceText.value.trim();
  if (!text) return;
  lines.value.push({ role: "me", text });
  loading.value = true;
  waitingHr.value = true;
  error.value = "";
  try {
    const data = await runtimeAdapter.voiceTurn(sessionId.value, { audio_file: makeDummyWav(text) });
    lines.value.push({ role: "hr", text: data.result.hr_reply });
    session.value = data.session;
    sessionStorage.setItem("currentSession", JSON.stringify(data.session));
    if (data.flow?.next_phase === "end" || data.result.is_game_over || data.session.status === "settled") {
      router.push(`/result/${sessionId.value}`);
      return;
    }
    if (data.flow?.next_phase === "text") {
      router.push(`/battle/${sessionId.value}`);
      return;
    }
    voiceText.value = "";
  } catch (e) {
    error.value = `语音回合失败：${String(e)}`;
  } finally {
    waitingHr.value = false;
    loading.value = false;
  }
}
</script>

<style scoped>
.page-root { width: 375px; height: 700px; }
.phone-shell { width: 100%; height: 100%; border-radius: 32px; overflow: hidden; position: relative; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a; background: #fff; }
.phone-notch { position: absolute; top: 8px; left: 50%; transform: translateX(-50%); width: 100px; height: 24px; background: #1a1a1a; border-radius: 0 0 16px 16px; z-index: 10; }
.status-bar { height: 36px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0; }
.status-bar.dark { background: #1a1a2e; }
.call-active-bg { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%); flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; align-items: center; padding: 20px 24px; position: relative; color: #fff; }
.call-avatar-large { width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #e8f5e9, #c8e6c9); display: flex; align-items: center; justify-content: center; font-size: 36px; margin-top: 20px; }
.call-name { font-size: 20px; font-weight: 600; margin-top: 12px; }
.call-role { color: rgba(255,255,255,0.7); font-size: 12px; margin-top: 2px; }
.call-company { color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 1px; }
.call-timer { color: rgba(255,255,255,0.6); font-size: 13px; margin-top: 16px; }
.call-hud { width: 100%; max-width: 300px; margin-top: 16px; }
.call-hud-label { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12px; }
.call-hud-bar { width: 100%; height: 4px; background: rgba(255,255,255,0.15); border-radius: 2px; overflow: hidden; }
.call-hud-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, #ff4757, #ffa502, #00c2a2); }
.call-transcript { flex: 1; min-height: 0; width: 100%; max-width: 320px; margin-top: 16px; overflow-y: auto; overscroll-behavior: contain; display: flex; flex-direction: column; gap: 8px; }
.call-transcript-line.me { display: flex; justify-content: flex-end; }
.call-transcript-bubble { padding: 8px 12px; border-radius: 12px; font-size: 12px; line-height: 1.5; max-width: 80%; word-break: break-word; overflow-wrap: anywhere; background: rgba(255,255,255,0.12); }
.call-transcript-line.me .call-transcript-bubble { background: rgba(0,194,162,0.3); }
.call-transcript-speaker { font-size: 9px; color: rgba(255,255,255,0.5); margin-bottom: 2px; }
.call-typing-bubble { display:flex; align-items:center; gap:4px; }
.call-typing-bubble span { width:6px; height:6px; border-radius:50%; background:rgba(255,255,255,0.65); animation: callDotPulse 1.1s infinite ease-in-out; }
.call-typing-bubble span:nth-child(3) { animation-delay: 0.15s; }
.call-typing-bubble span:nth-child(4) { animation-delay: 0.3s; }
@keyframes callDotPulse { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
.voice-input-row { width: 100%; max-width: 320px; display: flex; gap: 8px; margin-top: 10px; }
.voice-input-row input { flex: 1; border: none; border-radius: 12px; padding: 8px 10px; }
.voice-input-row button { border: none; border-radius: 12px; padding: 0 12px; background: #00c2a2; color: #fff; }
.call-actions { margin-top: 12px; padding-bottom: 16px; display: flex; justify-content: center; gap: 36px; }
.call-btn { width: 56px; height: 56px; border-radius: 50%; border: none; font-size: 22px; color: #fff; }
.call-btn-hangup { background: #ff4757; }
.call-btn-mute { width: 48px; height: 48px; font-size: 18px; background: rgba(255,255,255,0.15); }
.error { color: #ff9aa2; font-size: 12px; margin-top: 4px; }
</style>
