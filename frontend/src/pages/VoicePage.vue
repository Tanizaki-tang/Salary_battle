<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch"></div>
      <div class="status-bar dark">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>
      <div class="call-active-bg">
        <div class="call-avatar-large" :class="{ speaking: callPhase === 'speaking' }">👩‍💼</div>
        <div class="call-name">张敏</div>
        <div class="call-role">HR负责人</div>
        <div class="call-company">{{ callPhaseText }}</div>
        <div class="call-link-status">连线状态：{{ connectionStateText }}</div>
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
          <div v-if="streamingHrText && activeTurnGeneration === bargeGeneration" class="call-transcript-line hr">
            <div class="call-transcript-bubble">
              <div class="call-transcript-speaker">张敏</div>
              {{ streamingHrText }}
            </div>
          </div>
          <div v-else-if="callPhase === 'thinking'" class="call-transcript-line hr">
            <div class="call-transcript-bubble call-typing-bubble">
              <div class="call-transcript-speaker">对方思考中...</div>
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <div v-if="partialAsr && userSpeaking" class="asr-partial">🎧 {{ partialAsr }}</div>
        <div v-if="softHint" class="asr-partial soft-hint">{{ softHint }}</div>

        <div class="call-actions">
          <button class="call-btn call-btn-mute" title="文字战" @click="$router.push(`/battle/${sessionId}`)">💬</button>
          <button
            class="call-btn call-btn-mute"
            :class="{ active: selfMuted }"
            title="静音"
            @click="toggleSelfMute"
          >
            {{ selfMuted ? "🔇" : "🎤" }}
          </button>
          <button class="call-btn call-btn-hangup" title="挂断" @click="hangup">📞</button>
          <button class="call-btn call-btn-mute" title="首页" @click="$router.push('/')">⌂</button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { SessionState } from "../runtime/battle_runtime_adapter";
import { RealtimeWsClient, type CallPhase, type WsMessage } from "../runtime/ws_runtime_adapter";
import {
  createUtterance,
  ensureTtsVoices,
  loadTtsVoiceConfig,
  pickChineseVoice,
  shouldFlushTtsBuffer,
  type TtsVoiceConfig,
} from "../runtime/tts_voice";
import { EnergyVadMonitor, loadVadConfig } from "../runtime/vad";

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));
const loading = ref(false);
const error = ref("");
const softHint = ref("");
const lines = ref<Array<{ role: "hr" | "me"; text: string }>>([]);
const transcriptRef = ref<HTMLElement | null>(null);
const streamingHrText = ref("");
const partialAsr = ref("");
const session = ref<SessionState | null>(null);
const connectionState = ref<"connecting" | "ringing" | "ready" | "failed" | "offline">("offline");
const callPhase = ref<CallPhase | "ringing">("ringing");
const userSpeaking = ref(false);
const selfMuted = ref(false);
const realtimeEnabled = ((import.meta.env.VITE_REALTIME_WS_ENABLED || "true") as string).toLowerCase() !== "false";
const ttsEnabled = ((import.meta.env.VITE_REALTIME_TTS_ENABLED || "true") as string).toLowerCase() !== "false";
const recorderMimeType = ref("audio/webm");
let wsClient: RealtimeWsClient | null = null;
let mediaRecorder: MediaRecorder | null = null;
let mediaStream: MediaStream | null = null;
let audioTrack: MediaStreamTrack | null = null;
let vadMonitor: EnergyVadMonitor | null = null;
let unsubscribeEvent: (() => void) | null = null;
let ttsBuffer = "";
const ttsQueue: string[] = [];
let ttsSpeaking = false;
const ttsAudioQueue: string[] = [];
let ttsAudioPlaying = false;
let ttsAudio: HTMLAudioElement | null = null;
let ttsVoice: SpeechSynthesisVoice | null = null;
let ttsConfig: TtsVoiceConfig = loadTtsVoiceConfig();
let bargeGeneration = 0;
let activeTurnGeneration = 0;
let canCommit = true;
let utteranceActive = false;
let capturingUtterance = false;
let commitCooldownUntil = 0;
const commitCooldownMs = Number(import.meta.env.VITE_VAD_COMMIT_COOLDOWN_MS || 1200) || 1200;
let ringingTimer: number | null = null;
const startedAt = Date.now();
const nowTick = ref(Date.now());
const timerHandle = window.setInterval(() => {
  nowTick.value = Date.now();
}, 1000);

const cachedSession = sessionStorage.getItem("currentSession");
if (cachedSession) session.value = JSON.parse(cachedSession) as SessionState;

const timer = computed(() => {
  const sec = Math.floor((nowTick.value - startedAt) / 1000);
  const mm = String(Math.floor(sec / 60)).padStart(2, "0");
  const ss = String(sec % 60).padStart(2, "0");
  return `${mm}:${ss}`;
});

const callPhaseText = computed(() => {
  if (connectionState.value === "connecting") return "正在连接...";
  if (connectionState.value === "ringing") return "响铃中...";
  if (callPhase.value === "listening") return selfMuted.value ? "你已静音" : "正在听你说…";
  if (callPhase.value === "thinking") return "对方思考中…";
  if (callPhase.value === "speaking") return "对方正在说话…";
  return "通话中";
});

const connectionStateText = computed(() => {
  if (!realtimeEnabled) return "未启用实时语音";
  if (connectionState.value === "connecting") return "连接中";
  if (connectionState.value === "ringing") return "响铃中";
  if (connectionState.value === "ready") return "通话中";
  if (connectionState.value === "failed") return "连接失败";
  return "未连接";
});

function scrollTranscriptToBottom() {
  nextTick(() => {
    const el = transcriptRef.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

watch(
  () => [lines.value.length, callPhase.value, streamingHrText.value.length, partialAsr.value.length],
  () => scrollTranscriptToBottom(),
);

onMounted(async () => {
  if (ttsEnabled && "speechSynthesis" in window) {
    const voices = await ensureTtsVoices();
    ttsConfig = loadTtsVoiceConfig();
    ttsVoice = pickChineseVoice(voices, ttsConfig.preferredName);
  }
  if (!realtimeEnabled) {
    error.value = "实时语音未启用，请返回文字页继续谈判";
    return;
  }
  connectionState.value = "connecting";
  wsClient = new RealtimeWsClient();
  try {
    await wsClient.connect(sessionId.value);
    unsubscribeEvent = wsClient.onEvent(handleWsEvent);
    connectionState.value = "ringing";
    callPhase.value = "ringing";
    const delay = 600 + Math.floor(Math.random() * 600);
    ringingTimer = window.setTimeout(() => {
      connectionState.value = "ready";
      callPhase.value = "listening";
      void startAlwaysOnMic();
    }, delay);
  } catch {
    connectionState.value = "failed";
    error.value = "实时语音连接失败，请检查后端是否启动";
  }
});

onUnmounted(() => {
  window.clearInterval(timerHandle);
  if (ringingTimer !== null) window.clearTimeout(ringingTimer);
  stopAlwaysOnMic();
  cleanupSpeech();
  unsubscribeEvent?.();
  wsClient?.close();
  wsClient = null;
});

function isStaleTurn(): boolean {
  return activeTurnGeneration !== bargeGeneration;
}

function handleBargeIn() {
  if (callPhase.value !== "speaking" && callPhase.value !== "thinking") return;
  bargeGeneration += 1;
  cleanupSpeech();
  streamingHrText.value = "";
  wsClient?.sendBargeIn();
  callPhase.value = "listening";
  canCommit = true;
  loading.value = false;
  commitCooldownUntil = 0;
}

function handleWsEvent(message: WsMessage) {
  const payload = (message.payload || {}) as Record<string, any>;
  if (message.type === "server.call_state") {
    const phase = String(payload.phase || "") as CallPhase;
    if (phase === "listening" || phase === "thinking" || phase === "speaking") {
      if (!isStaleTurn() || phase === "listening") {
        callPhase.value = phase;
      }
    }
    return;
  }
  if (message.type === "server.asr_partial") {
    if (capturingUtterance && userSpeaking.value) {
      partialAsr.value = String(payload.text || "正在识别...");
    }
    return;
  }
  if (message.type === "server.asr_final") {
    partialAsr.value = "";
    userSpeaking.value = false;
    const transcript = String(payload.transcript || "").trim();
    if (transcript) lines.value.push({ role: "me", text: transcript });
    return;
  }
  if (message.type === "server.asr_skipped") {
    partialAsr.value = "";
    userSpeaking.value = false;
    capturingUtterance = false;
    utteranceActive = false;
    loading.value = false;
    canCommit = true;
    commitCooldownUntil = Date.now() + commitCooldownMs;
    callPhase.value = "listening";
    softHint.value = "没听清，请再说一次";
    window.setTimeout(() => {
      softHint.value = "";
    }, 2000);
    return;
  }
  if (message.type === "server.hr_delta") {
    if (isStaleTurn()) return;
    callPhase.value = "speaking";
    streamingHrText.value += String(payload.delta || "");
    return;
  }
  if (message.type === "server.hr_audio_chunk") {
    if (isStaleTurn()) return;
    callPhase.value = "speaking";
    const audioB64 = String(payload.audio_b64 || "").trim();
    if (audioB64) {
      enqueueBackendTtsAudio(audioB64, String(payload.mime_type || "audio/wav"));
      return;
    }
    enqueueTtsChunk(String(payload.text || ""));
    return;
  }
  if (message.type === "server.turn_done") {
    if (isStaleTurn()) return;
    loading.value = false;
    canCommit = true;
    commitCooldownUntil = Date.now() + commitCooldownMs;
    capturingUtterance = false;
    utteranceActive = false;
    const result = payload.result || {};
    const flow = payload.flow || {};
    const nextSession = payload.session as SessionState | undefined;
    const finalReply = String(result.hr_reply || streamingHrText.value || "").trim();
    if (finalReply) lines.value.push({ role: "hr", text: finalReply });
    flushTtsBuffer();
    streamingHrText.value = "";
    partialAsr.value = "";
    userSpeaking.value = false;
    if (nextSession) {
      session.value = nextSession;
      sessionStorage.setItem("currentSession", JSON.stringify(nextSession));
    }
    if (!ttsAudioPlaying && !ttsSpeaking) {
      callPhase.value = "listening";
    }
    if (flow.next_phase === "end" || result.is_game_over || nextSession?.status === "settled") {
      void router.push(`/result/${sessionId.value}`);
      return;
    }
    if (flow.next_phase === "text") {
      void router.push(`/battle/${sessionId.value}`);
    }
    return;
  }
  if (message.type === "server.error") {
    loading.value = false;
    canCommit = true;
    commitCooldownUntil = Date.now() + commitCooldownMs;
    capturingUtterance = false;
    utteranceActive = false;
    partialAsr.value = "";
    userSpeaking.value = false;
    callPhase.value = "listening";
    const code = String(payload.code || "");
    if (code === "asr_empty" || code === "asr_failed") {
      softHint.value = code === "asr_failed" ? "识别失败，请重试" : "没听清，请再说一次";
      window.setTimeout(() => {
        softHint.value = "";
      }, 2500);
      return;
    }
    error.value = String(payload.message || "实时语音异常");
  }
}

async function startAlwaysOnMic() {
  if (!wsClient) return;
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    audioTrack = mediaStream.getAudioTracks()[0] || null;
    const preferred = ["audio/webm;codecs=opus", "audio/webm"];
    const picked = preferred.find((m) => MediaRecorder.isTypeSupported(m)) || "";
    recorderMimeType.value = picked || "audio/webm";
    mediaRecorder = picked
      ? new MediaRecorder(mediaStream, { mimeType: picked })
      : new MediaRecorder(mediaStream);
    mediaRecorder.ondataavailable = async (evt) => {
      if (!evt.data || evt.data.size <= 0 || !wsClient || selfMuted.value || !capturingUtterance) return;
      await wsClient.sendVoiceChunk(evt.data, recorderMimeType.value);
    };
    mediaRecorder.start(200);

    const vadConfig = loadVadConfig();
    vadMonitor = new EnergyVadMonitor(vadConfig, {
      onSpeechStart: () => {
        if (selfMuted.value || !canCommit || Date.now() < commitCooldownUntil) return;
        utteranceActive = true;
        capturingUtterance = true;
        userSpeaking.value = true;
        partialAsr.value = "正在听你说…";
        wsClient?.resetUtterance();
        if (callPhase.value === "speaking" || callPhase.value === "thinking" || ttsAudioPlaying || ttsSpeaking) {
          handleBargeIn();
          capturingUtterance = true;
        }
      },
      onSpeechCancel: () => {
        capturingUtterance = false;
        utteranceActive = false;
        userSpeaking.value = false;
        partialAsr.value = "";
      },
      onSpeechEnd: () => {
        if (selfMuted.value || !canCommit || loading.value || Date.now() < commitCooldownUntil) {
          capturingUtterance = false;
          utteranceActive = false;
          userSpeaking.value = false;
          partialAsr.value = "";
          return;
        }
        if (!utteranceActive) return;
        utteranceActive = false;
        capturingUtterance = false;
        userSpeaking.value = false;
        commitCurrentUtterance();
      },
    });
    vadMonitor.start(mediaStream);
  } catch {
    error.value = "无法访问麦克风，请检查浏览器权限";
    connectionState.value = "failed";
  }
}

function commitCurrentUtterance() {
  if (!wsClient || loading.value || selfMuted.value) return;
  loading.value = true;
  canCommit = false;
  activeTurnGeneration = bargeGeneration;
  callPhase.value = "thinking";
  partialAsr.value = "";
  wsClient.commitUtterance(recorderMimeType.value);
}

function stopAlwaysOnMic() {
  vadMonitor?.stop();
  vadMonitor = null;
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    try {
      mediaRecorder.stop();
    } catch {
      // ignore
    }
  }
  mediaRecorder = null;
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  audioTrack = null;
  userSpeaking.value = false;
}

function toggleSelfMute() {
  selfMuted.value = !selfMuted.value;
  if (audioTrack) audioTrack.enabled = !selfMuted.value;
  vadMonitor?.setEnabled(!selfMuted.value);
  if (selfMuted.value) {
    userSpeaking.value = false;
    partialAsr.value = "";
    utteranceActive = false;
    capturingUtterance = false;
  }
}

function hangup() {
  stopAlwaysOnMic();
  cleanupSpeech();
  wsClient?.close();
  void router.push(`/result/${sessionId.value}`);
}

function cleanupSpeech() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  ttsBuffer = "";
  ttsQueue.length = 0;
  ttsSpeaking = false;
  if (ttsAudio) {
    try {
      const url = ttsAudio.src;
      ttsAudio.pause();
      ttsAudio.src = "";
      if (url.startsWith("blob:")) URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  }
  ttsAudio = null;
  ttsAudioQueue.forEach((u) => URL.revokeObjectURL(u));
  ttsAudioQueue.length = 0;
  ttsAudioPlaying = false;
}

function enqueueTtsChunk(chunk: string) {
  if (!ttsEnabled || !chunk || !("speechSynthesis" in window)) return;
  ttsBuffer += chunk;
  if (shouldFlushTtsBuffer(ttsBuffer, chunk)) {
    ttsQueue.push(ttsBuffer.trim());
    ttsBuffer = "";
    playTtsQueue();
  }
}

function flushTtsBuffer() {
  if (!ttsEnabled || !("speechSynthesis" in window)) return;
  const pending = ttsBuffer.trim();
  if (pending) {
    ttsQueue.push(pending);
    ttsBuffer = "";
  }
  playTtsQueue();
}

function playTtsQueue() {
  if (ttsSpeaking || ttsQueue.length === 0 || !("speechSynthesis" in window)) return;
  const text = ttsQueue.shift()?.trim();
  if (!text) return;
  ttsSpeaking = true;
  const utter = createUtterance(text, ttsVoice, ttsConfig);
  utter.onend = () => {
    ttsSpeaking = false;
    if (!ttsSpeaking && ttsQueue.length === 0 && !loading.value) {
      callPhase.value = "listening";
    }
    playTtsQueue();
  };
  utter.onerror = () => {
    ttsSpeaking = false;
    playTtsQueue();
  };
  window.speechSynthesis.speak(utter);
}

function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function enqueueBackendTtsAudio(audioB64: string, mimeType: string) {
  if (!ttsEnabled || !audioB64 || isStaleTurn()) return;
  const bytes = base64ToBytes(audioB64);
  const blob = new Blob([bytes], { type: mimeType || "audio/wav" });
  const url = URL.createObjectURL(blob);
  ttsAudioQueue.push(url);
  playBackendTtsQueue();
}

function playBackendTtsQueue() {
  if (ttsAudioPlaying || ttsAudioQueue.length === 0 || isStaleTurn()) return;
  const url = ttsAudioQueue.shift();
  if (!url) return;
  ttsAudioPlaying = true;
  callPhase.value = "speaking";
  const audio = new Audio(url);
  ttsAudio = audio;
  const finish = () => {
    ttsAudioPlaying = false;
    ttsAudio = null;
    URL.revokeObjectURL(url);
    if (ttsAudioQueue.length === 0 && !loading.value && !isStaleTurn()) {
      callPhase.value = "listening";
    }
    playBackendTtsQueue();
  };
  audio.onended = finish;
  audio.onerror = finish;
  void audio.play().catch(finish);
}

// Track utterance activity for VAD end detection
watch(userSpeaking, (speaking) => {
  if (!speaking) utteranceActive = false;
});
</script>

<style scoped>
.page-root { width: 375px; height: 700px; }
.phone-shell { width: 100%; height: 100%; border-radius: 32px; overflow: hidden; position: relative; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a; background: #fff; }
.phone-notch { position: absolute; top: 8px; left: 50%; transform: translateX(-50%); width: 100px; height: 24px; background: #1a1a1a; border-radius: 0 0 16px 16px; z-index: 10; }
.status-bar { height: 36px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0; }
.status-bar.dark { background: #1a1a2e; }
.call-active-bg { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%); flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; align-items: center; padding: 20px 24px; position: relative; color: #fff; }
.call-avatar-large { width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #e8f5e9, #c8e6c9); display: flex; align-items: center; justify-content: center; font-size: 36px; margin-top: 20px; transition: box-shadow 0.3s ease; }
.call-avatar-large.speaking { animation: avatarPulse 1.2s ease-in-out infinite; box-shadow: 0 0 0 8px rgba(0, 194, 162, 0.25); }
@keyframes avatarPulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
.call-name { font-size: 20px; font-weight: 600; margin-top: 12px; }
.call-role { color: rgba(255,255,255,0.7); font-size: 12px; margin-top: 2px; }
.call-company { color: rgba(255,255,255,0.72); font-size: 13px; margin-top: 4px; min-height: 18px; }
.call-link-status { color: rgba(255,255,255,0.55); font-size: 11px; margin-top: 4px; }
.call-timer { color: rgba(255,255,255,0.6); font-size: 13px; margin-top: 12px; }
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
.asr-partial { width: 100%; max-width: 320px; margin-top: 8px; font-size: 11px; color: rgba(255,255,255,0.86); }
.soft-hint { color: rgba(255,255,255,0.55); font-style: italic; }
.call-actions { margin-top: auto; padding-bottom: 16px; display: flex; justify-content: center; gap: 24px; align-items: center; }
.call-btn { width: 56px; height: 56px; border-radius: 50%; border: none; font-size: 22px; color: #fff; cursor: pointer; }
.call-btn-hangup { background: #ff4757; }
.call-btn-mute { width: 48px; height: 48px; font-size: 18px; background: rgba(255,255,255,0.15); }
.call-btn-mute.active { background: rgba(255, 71, 87, 0.45); }
.error { color: #ff9aa2; font-size: 12px; margin-top: 4px; text-align: center; }
</style>
