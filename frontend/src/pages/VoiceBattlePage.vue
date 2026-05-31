<template>
  <section class="vb-stage">
    <div class="phone-shell">
      <div class="phone-notch" />
      <div class="status-bar">
        <span>{{ nowTime }}</span>
        <span>📶 🔋</span>
      </div>

      <div class="call-body">
        <div class="call-top">
          <button type="button" class="call-back" @click="$router.push('/')">‹</button>
          <div class="call-kpi">
            <span class="kpi-chip">💰 {{ salaryHudText }}</span>
            <span class="kpi-chip">⏱️ {{ workHoursText }}</span>
            <span class="kpi-chip">🛡️ {{ securityText }}</span>
          </div>
        </div>

        <div class="call-contact">
          <img class="call-avatar" :src="bossAvatarUrl" alt="HR" />
          <div class="call-name">{{ hrName }}</div>
          <div class="call-sub">
            <span>{{ statusText }}</span>
            <span v-if="running && callTimerText"> · {{ callTimerText }}</span>
          </div>
        </div>

        <div class="call-captions" :class="{ collapsed: !showCaptions }">
          <div class="caption-row hr">
            <div class="caption-badge">HR</div>
            <div class="caption-text">{{ hrCaption }}</div>
          </div>
          <div class="caption-row me">
            <div class="caption-badge">我</div>
            <div class="caption-text">{{ meCaption }}</div>
          </div>
          <button type="button" class="caption-toggle" @click="showCaptions = !showCaptions">
            {{ showCaptions ? "收起字幕" : "展开字幕" }}
          </button>
        </div>
      </div>

      <div class="call-controls">
        <button type="button" class="ctl-btn" :disabled="!running" :class="{ on: !micMuted }" @click="toggleMic">
          <span class="ctl-emoji">🎙️</span>
          <span class="ctl-label">{{ micMuted ? "已静音" : "麦克风" }}</span>
        </button>
        <button
          type="button"
          class="ctl-btn"
          :disabled="!running"
          :class="{ on: speakerOn }"
          @click="toggleSpeaker"
        >
          <span class="ctl-emoji">🔊</span>
          <span class="ctl-label">{{ speakerOn ? "扬声器" : "听筒" }}</span>
        </button>
        <button type="button" class="ctl-btn" :disabled="true">
          <span class="ctl-emoji">⌨️</span>
          <span class="ctl-label">键盘</span>
        </button>
      </div>

      <div class="call-action">
        <button
          type="button"
          class="call-action-btn"
          :class="running ? 'hangup' : 'pickup'"
          @click="running ? stopCall() : startCall()"
        >
          {{ running ? "挂断" : "接听" }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { bossAvatarUrl } from "../assets/avatars";
import type { SessionState } from "../runtime/battle_runtime_adapter";
import { Pcm16MicrophoneCapture } from "../runtime/pcm16_capture";
import { PcmStreamPlayer } from "../runtime/pcm_stream_player";
import { connectVoiceBattle } from "../runtime/voice_battle_ws";

const route = useRoute();
const sessionId = computed(() => String(route.params.sessionId || ""));

const running = ref(false);
const statusText = ref("未连接");
const asrText = ref("");
const hrText = ref("");
const session = ref<SessionState | null>(null);
const showCaptions = ref(true);
const micMuted = ref(false);
const speakerOn = ref(true);
const callStartedAt = ref<number | null>(null);
const nowTime = ref(new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }));
let clockTimer: number | null = null;
let callTimer: number | null = null;
const callElapsedSec = ref(0);

const capture = new Pcm16MicrophoneCapture(16000, 40);
const player = new PcmStreamPlayer();
let wsConn: ReturnType<typeof connectVoiceBattle> | null = null;

const callTimerText = computed(() => {
  const sec = callElapsedSec.value;
  if (!running.value || sec <= 0) return "";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
});

const hrName = computed(() => {
  try {
    const raw = sessionStorage.getItem("hrPersonalityMeta");
    if (!raw) return "HR";
    const meta = JSON.parse(raw) as { name?: string; emoji?: string };
    if (meta?.name) return `${meta.emoji || "😊"} ${meta.name}`;
  } catch {}
  return "HR";
});

function lastText(input: string, maxLen = 180) {
  const s = (input || "").trim();
  if (!s) return "…";
  return s.length <= maxLen ? s : s.slice(-maxLen);
}

const hrCaption = computed(() => lastText(hrText.value, 220));
const meCaption = computed(() => lastText(asrText.value, 140));

function formatMaybeFloat(value: number) {
  if (!Number.isFinite(value)) return "-";
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 1e-6) return String(rounded);
  return value.toFixed(1);
}

const salaryHudText = computed(() => {
  const offer = session.value?.current_salary_offer;
  if (!offer) return "-";
  return `${Math.round(Number(offer) / 1000)}K`;
});

const workHoursText = computed(() => {
  const value = session.value?.work_hours;
  if (value == null) return "-";
  return formatMaybeFloat(Number(value));
});

const securityText = computed(() => {
  const value = session.value?.security;
  if (value == null) return "-";
  return formatMaybeFloat(Number(value));
});

function toggleMic() {
  micMuted.value = !micMuted.value;
}

function toggleSpeaker() {
  speakerOn.value = !speakerOn.value;
}

function startTimers() {
  if (clockTimer == null) {
    clockTimer = window.setInterval(() => {
      nowTime.value = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    }, 1000);
  }
  if (callTimer == null) {
    callTimer = window.setInterval(() => {
      if (!callStartedAt.value) return;
      callElapsedSec.value = Math.max(0, Math.floor((Date.now() - callStartedAt.value) / 1000));
    }, 300);
  }
}

function stopTimers() {
  if (callTimer != null) {
    window.clearInterval(callTimer);
    callTimer = null;
  }
  if (clockTimer != null) {
    window.clearInterval(clockTimer);
    clockTimer = null;
  }
}

async function startCall() {
  if (running.value) return;
  running.value = true;
  statusText.value = "连接中…";
  asrText.value = "";
  hrText.value = "";
  callElapsedSec.value = 0;
  callStartedAt.value = null;
  micMuted.value = false;
  speakerOn.value = true;
  startTimers();

  wsConn = connectVoiceBattle(sessionId.value, {
    onEvent: (evt) => {
      if (evt.type === "ready") {
        statusText.value = "通话中";
        callStartedAt.value = Date.now();
      } else if (evt.type === "asr.partial") {
        asrText.value = evt.text;
      } else if (evt.type === "asr.final") {
        asrText.value = evt.text;
      } else if (evt.type === "hr.text.delta") {
        hrText.value += evt.text;
      } else if (evt.type === "hr.audio.delta") {
        if (speakerOn.value) {
          player.playPcm16Base64(evt.audio_b64, evt.sample_rate);
        }
      } else if (evt.type === "turn.done") {
        session.value = evt.session;
      } else if (evt.type === "error") {
        statusText.value = evt.message;
      }
    },
  });

  wsConn.ws.onopen = async () => {
    try {
      await capture.start({
        onFrame: (pcm16) => {
          if (micMuted.value) return;
          wsConn?.sendAudio(pcm16);
        },
      });
    } catch (e) {
      statusText.value = `麦克风不可用：${String(e)}`;
      stopCall();
    }
  };

  wsConn.ws.onclose = () => {
    if (running.value) statusText.value = "连接已断开";
    running.value = false;
    callStartedAt.value = null;
    callElapsedSec.value = 0;
  };
}

function stopCall() {
  if (!running.value) return;
  running.value = false;
  capture.stop();
  wsConn?.close();
  wsConn = null;
  callStartedAt.value = null;
  callElapsedSec.value = 0;
  stopTimers();
}

onMounted(() => {
  startTimers();
});

onUnmounted(() => {
  stopCall();
  player.stop();
  stopTimers();
});
</script>

<style scoped>
.vb-stage {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background:
    radial-gradient(ellipse 90% 70% at 50% 0%, rgba(0, 194, 162, 0.22), transparent 60%),
    radial-gradient(ellipse 70% 60% at 100% 100%, rgba(250, 107, 61, 0.14), transparent 55%),
    linear-gradient(160deg, #0a1628 0%, #0d2137 45%, #091018 100%);
}

.phone-shell {
  width: 375px;
  height: 700px;
  border-radius: 32px;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45), 0 0 0 2px #1a1a1a;
  background: rgba(10, 22, 40, 0.96);
}

.phone-notch {
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 100px;
  height: 24px;
  background: #1a1a1a;
  border-radius: 0 0 16px 16px;
  z-index: 20;
}

.status-bar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}

.call-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 10px 18px 0;
  position: relative;
}

.call-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.call-back {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
  font-size: 22px;
}

.call-kpi {
  display: flex;
  gap: 8px;
  min-width: 0;
  justify-content: flex-end;
}

.kpi-chip {
  padding: 6px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.9);
  font-size: 11px;
  font-weight: 700;
}

.call-contact {
  padding-top: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.call-avatar {
  width: 112px;
  height: 112px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.35);
  border: 2px solid rgba(255, 255, 255, 0.18);
}

.call-name {
  color: #fff;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.call-sub {
  color: rgba(255, 255, 255, 0.75);
  font-size: 12px;
  font-weight: 600;
}

.call-captions {
  margin-top: 16px;
  padding: 10px 12px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.call-captions.collapsed .caption-row {
  display: none;
}

.caption-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.caption-badge {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  background: rgba(0, 0, 0, 0.28);
  color: rgba(255, 255, 255, 0.9);
}

.caption-row.hr .caption-badge {
  background: rgba(250, 107, 61, 0.22);
}

.caption-row.me .caption-badge {
  background: rgba(0, 194, 162, 0.22);
}

.caption-text {
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.caption-toggle {
  margin-top: 2px;
  align-self: flex-end;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.72);
  font-size: 11px;
  font-weight: 700;
}

.call-controls {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  padding: 10px 22px 0;
}

.ctl-btn {
  border: none;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 10px;
}

.ctl-btn:disabled {
  opacity: 0.45;
}

.ctl-btn.on {
  background: rgba(0, 194, 162, 0.16);
  border-color: rgba(0, 194, 162, 0.28);
}

.ctl-emoji {
  font-size: 22px;
}

.ctl-label {
  font-size: 11px;
  font-weight: 800;
}

.call-action {
  padding: 14px 22px 22px;
}

.call-action-btn {
  width: 100%;
  height: 56px;
  border-radius: 999px;
  border: none;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 0.06em;
  color: #fff;
}

.call-action-btn.pickup {
  background: linear-gradient(135deg, #00c2a2 0%, #2ed573 100%);
}

.call-action-btn.hangup {
  background: linear-gradient(135deg, #ff4757 0%, #fa6b3d 100%);
}

@media (max-width: 420px) {
  .vb-stage {
    padding: 0;
  }
  .phone-shell {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
    box-shadow: none;
  }
  .phone-notch {
    top: 0;
  }
}
</style>
