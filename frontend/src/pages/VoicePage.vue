<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch"></div>
      <div class="status-bar dark">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>
      <div class="call-active-bg" @click="unlockMicIfNeeded">
        <img class="call-avatar-large" :class="{ speaking: callPhase === 'speaking' }" :src="bossAvatarUrl" alt="HR" />
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
        <div v-if="micHint" class="asr-partial soft-hint">{{ micHint }}</div>
        <div v-if="softHint" class="asr-partial soft-hint">{{ softHint }}</div>

        <div class="call-actions">
          <button class="call-btn call-btn-hangup" title="挂断" @click="hangup">📞</button>
          <button
            class="call-btn call-btn-ptt"
            :class="{ active: manualSpeaking }"
            title="按住说话"
            @mousedown.prevent="beginManualSpeak"
            @mouseup.prevent="endManualSpeak"
            @mouseleave="endManualSpeak"
            @touchstart.prevent="beginManualSpeak"
            @touchend.prevent="endManualSpeak"
            @touchcancel="endManualSpeak"
          >
            🎙
          </button>
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
import { bossAvatarUrl } from "../assets/avatars";
import { EnergyVadMonitor, loadVadConfig } from "../runtime/vad";

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));
const loading = ref(false);
const error = ref("");
const softHint = ref("");
const micHint = ref("");
const manualSpeaking = ref(false);
const lines = ref<Array<{ role: "hr" | "me"; text: string }>>([]);
const transcriptRef = ref<HTMLElement | null>(null);
const streamingHrText = ref("");
const partialAsr = ref("");
const session = ref<SessionState | null>(null);
const connectionState = ref<"connecting" | "ringing" | "ready" | "failed" | "offline">("offline");
const callPhase = ref<CallPhase | "ringing">("ringing");
const userSpeaking = ref(false);
const realtimeEnabled = ((import.meta.env.VITE_REALTIME_WS_ENABLED || "true") as string).toLowerCase() !== "false";
const ttsEnabled = ((import.meta.env.VITE_REALTIME_TTS_ENABLED || "true") as string).toLowerCase() !== "false";
const latencyDebug = ((import.meta.env.VITE_LATENCY_DEBUG || "false") as string).toLowerCase() !== "false";
const pcmAsrEnabled = ((import.meta.env.VITE_REALTIME_ASR_PCM || "false") as string).toLowerCase() !== "false";
const pcmAsrSampleRate = Number(import.meta.env.VITE_REALTIME_ASR_SAMPLE_RATE || 16000) || 16000;
const recorderMimeType = ref(pcmAsrEnabled ? `audio/pcm;rate=${pcmAsrSampleRate}` : "audio/webm");
let wsClient: RealtimeWsClient | null = null;
let utteranceRecorder: MediaRecorder | null = null;
let mediaStream: MediaStream | null = null;
let pcmAudioContext: AudioContext | null = null;
let pcmSourceNode: MediaStreamAudioSourceNode | null = null;
let pcmProcessor: ScriptProcessorNode | null = null;
let pcmSilenceGain: GainNode | null = null;
let pcmPendingSamples: number[] = [];
let pcmSentBytes = 0;
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
let manualSpeakActive = false;
let micStarted = false;
let utteranceActive = false;
let capturingUtterance = false;
let commitCooldownUntil = 0;
const commitCooldownMs = Number(import.meta.env.VITE_VAD_COMMIT_COOLDOWN_MS || 1200) || 1200;
let openingInProgress = false;
let playbackIdleCallback: (() => void) | null = null;
let openingSafetyTimer: number | null = null;
let openingFallbackTimer: number | null = null;
const utteranceChunks: Blob[] = [];
const MIN_UTTERANCE_MS = 450;
let manualSpeakStartedAt = 0;
let ringingTimer: number | null = null;
let latSpeechStartAt = 0;
let latFirstUpFrameAt = 0;
let latFirstAsrPartialAt = 0;
let latAsrFinalAt = 0;
let latFirstHrDeltaAt = 0;
let latFirstHrAudioAt = 0;
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
  if (callPhase.value === "listening") return "正在听你说…";
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
    micHint.value = "接通中…请允许麦克风权限";
    await startAlwaysOnMic();
    connectionState.value = "ready";
    callPhase.value = "speaking";
    micHint.value = "对方正在打招呼…";
    openingFallbackTimer = window.setTimeout(playLocalOpeningFallback, 2500);
  } catch {
    connectionState.value = "failed";
    error.value = "实时语音连接失败，请检查后端是否启动";
  }
});

onUnmounted(() => {
  window.clearInterval(timerHandle);
  if (ringingTimer !== null) window.clearTimeout(ringingTimer);
  if (openingSafetyTimer !== null) window.clearTimeout(openingSafetyTimer);
  if (openingFallbackTimer !== null) window.clearTimeout(openingFallbackTimer);
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

function finishOpeningPlayback() {
  if (openingSafetyTimer !== null) {
    window.clearTimeout(openingSafetyTimer);
    openingSafetyTimer = null;
  }
  openingInProgress = false;
  canCommit = true;
  vadMonitor?.setEnabled(true);
  if (!loading.value && !ttsAudioPlaying && !ttsSpeaking) {
    callPhase.value = "listening";
  }
  micHint.value = "直接说话，或按住 🎙 说话";
  window.setTimeout(() => {
    if (micHint.value === "直接说话，或按住 🎙 说话") micHint.value = "";
  }, 3000);
}

function startOpeningSafetyTimer() {
  if (openingSafetyTimer !== null) window.clearTimeout(openingSafetyTimer);
  openingSafetyTimer = window.setTimeout(() => {
    if (openingInProgress) finishOpeningPlayback();
  }, 15000);
}

function playHrOpening(text: string, audioB64: string, mimeType: string) {
  if (!text.trim()) {
    finishOpeningPlayback();
    return;
  }
  openingInProgress = true;
  canCommit = false;
  vadMonitor?.setEnabled(false);
  startOpeningSafetyTimer();
  lines.value.push({ role: "hr", text: text.trim() });
  callPhase.value = "speaking";
  if (audioB64 && ttsEnabled) {
    enqueueBackendTtsAudio(audioB64, mimeType || "audio/wav", finishOpeningPlayback);
    return;
  }
  if (ttsEnabled && "speechSynthesis" in window) {
    playbackIdleCallback = finishOpeningPlayback;
    ttsQueue.push(text.trim());
    playTtsQueue();
    return;
  }
  window.setTimeout(finishOpeningPlayback, Math.max(1500, text.length * 120));
}

function playLocalOpeningFallback() {
  openingFallbackTimer = null;
  if (openingInProgress || lines.value.some((m) => m.role === "hr")) return;
  const opening = sessionStorage.getItem("hrOpening")?.trim();
  if (!opening) return;
  playHrOpening(opening, "", "");
}

function handleWsEvent(message: WsMessage) {
  const payload = (message.payload || {}) as Record<string, any>;
  const serverDelay = typeof message.ts === "number" ? Date.now() - message.ts : null;
  if (latencyDebug && serverDelay !== null && serverDelay >= 0 && serverDelay <= 60000) {
    if (message.type === "server.asr_partial" || message.type === "server.asr_final" || message.type === "server.hr_delta") {
      console.log("[latency] server_delay_ms", message.type, serverDelay);
    }
  }
  if (message.type === "server.hr_opening") {
    if (openingFallbackTimer !== null) {
      window.clearTimeout(openingFallbackTimer);
      openingFallbackTimer = null;
    }
    if (lines.value.some((m) => m.role === "hr")) return;
    const text = String(payload.text || "").trim();
    const audioB64 = String(payload.audio_b64 || "").trim();
    playHrOpening(text, audioB64, String(payload.mime_type || "audio/wav"));
    return;
  }
  if (message.type === "server.call_state") {
    const phase = String(payload.phase || "") as CallPhase;
    if (openingInProgress && phase === "listening") return;
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
      if (latencyDebug && latFirstAsrPartialAt === 0 && latSpeechStartAt > 0) {
        latFirstAsrPartialAt = performance.now();
        console.log("[latency] first_asr_partial_ms", (latFirstAsrPartialAt - latSpeechStartAt).toFixed(1));
      }
    }
    return;
  }
  if (message.type === "server.asr_final") {
    partialAsr.value = "";
    userSpeaking.value = false;
    const transcript = String(payload.transcript || "").trim();
    if (transcript) lines.value.push({ role: "me", text: transcript });
    if (latencyDebug && latSpeechStartAt > 0) {
      latAsrFinalAt = performance.now();
      console.log("[latency] asr_final_ms", (latAsrFinalAt - latSpeechStartAt).toFixed(1), "len", transcript.length);
    }
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
    if (latencyDebug && latFirstHrDeltaAt === 0 && latSpeechStartAt > 0) {
      latFirstHrDeltaAt = performance.now();
      console.log("[latency] first_hr_delta_ms", (latFirstHrDeltaAt - latSpeechStartAt).toFixed(1));
    }
    return;
  }
  if (message.type === "server.hr_audio_chunk") {
    if (isStaleTurn()) return;
    callPhase.value = "speaking";
    const audioB64 = String(payload.audio_b64 || "").trim();
    if (audioB64) {
      if (latencyDebug && latFirstHrAudioAt === 0 && latSpeechStartAt > 0) {
        latFirstHrAudioAt = performance.now();
        console.log("[latency] first_hr_audio_ms", (latFirstHrAudioAt - latSpeechStartAt).toFixed(1));
      }
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

function unlockMicIfNeeded() {
  vadMonitor?.resumeAudio();
  if (!micStarted) void startAlwaysOnMic();
}

function beginUtteranceCapture() {
  if (openingInProgress) return false;
  const hrActive =
    callPhase.value === "speaking" ||
    callPhase.value === "thinking" ||
    ttsAudioPlaying ||
    ttsSpeaking;
  if (hrActive) {
    handleBargeIn();
  } else if (loading.value) {
    return false;
  }
  utteranceActive = true;
  capturingUtterance = true;
  userSpeaking.value = true;
  partialAsr.value = "正在听你说…";
  utteranceChunks.length = 0;
  pcmPendingSamples = [];
  pcmSentBytes = 0;
  latSpeechStartAt = performance.now();
  latFirstUpFrameAt = 0;
  latFirstAsrPartialAt = 0;
  latAsrFinalAt = 0;
  latFirstHrDeltaAt = 0;
  latFirstHrAudioAt = 0;
  wsClient?.resetUtterance();
  startUtteranceRecorder();
  return true;
}

function beginManualSpeak() {
  void beginManualSpeakAsync();
}

async function beginManualSpeakAsync() {
  unlockMicIfNeeded();
  if (manualSpeakActive || loading.value) return;
  if (openingInProgress) {
    cleanupSpeech();
    finishOpeningPlayback();
  }
  if (!micStarted) {
    await startAlwaysOnMic();
    if (!micStarted) {
      micHint.value = "请先允许麦克风权限，再按住 🎙 说话";
      return;
    }
    connectionState.value = "ready";
    callPhase.value = "listening";
  }
  manualSpeakActive = true;
  manualSpeaking.value = true;
  manualSpeakStartedAt = Date.now();
  vadMonitor?.setEnabled(false);
  if (!beginUtteranceCapture()) {
    manualSpeakActive = false;
    manualSpeaking.value = false;
    vadMonitor?.setEnabled(true);
  }
}

function cancelUtteranceCapture() {
  stopUtteranceRecorder();
  utteranceChunks.length = 0;
  wsClient?.resetUtterance();
  capturingUtterance = false;
  utteranceActive = false;
  userSpeaking.value = false;
  partialAsr.value = "";
}

function endManualSpeak() {
  if (!manualSpeakActive) return;
  manualSpeakActive = false;
  manualSpeaking.value = false;
  vadMonitor?.setEnabled(true);
  const heldMs = Date.now() - manualSpeakStartedAt;
  if (heldMs < MIN_UTTERANCE_MS) {
    cancelUtteranceCapture();
    softHint.value = "请按住 🎙 至少半秒再松手";
    window.setTimeout(() => {
      softHint.value = "";
    }, 2000);
    return;
  }
  void finishUtteranceAndCommit();
}

function createUtteranceRecorder(): MediaRecorder | null {
  if (pcmAsrEnabled) return null;
  if (!mediaStream) return null;
  const preferred = ["audio/webm;codecs=opus", "audio/webm"];
  const picked = preferred.find((m) => MediaRecorder.isTypeSupported(m)) || "";
  recorderMimeType.value = picked || "audio/webm";
  const recorder = picked
    ? new MediaRecorder(mediaStream, { mimeType: picked })
    : new MediaRecorder(mediaStream);
  recorder.ondataavailable = (evt) => {
    if (!evt.data || evt.data.size <= 0 || !capturingUtterance) return;
    utteranceChunks.push(evt.data);
  };
  return recorder;
}

function stopUtteranceRecorder() {
  if (pcmAsrEnabled) {
    stopPcmRecorder();
    return;
  }
  if (!utteranceRecorder) return;
  if (utteranceRecorder.state !== "inactive") {
    try {
      utteranceRecorder.stop();
    } catch {
      // ignore
    }
  }
  utteranceRecorder = null;
}

function startUtteranceRecorder() {
  stopUtteranceRecorder();
  if (pcmAsrEnabled) {
    startPcmRecorder();
    return;
  }
  const recorder = createUtteranceRecorder();
  if (!recorder) return;
  utteranceRecorder = recorder;
  utteranceRecorder.start(200);
}

async function flushUtteranceRecorder(): Promise<void> {
  if (pcmAsrEnabled) {
    await flushPcmRecorder();
    return;
  }
  const recorder = utteranceRecorder;
  if (!recorder || recorder.state !== "recording") {
    utteranceRecorder = null;
    return;
  }
  await new Promise<void>((resolve) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    recorder.addEventListener("stop", done, { once: true });
    try {
      recorder.requestData();
    } catch {
      // ignore
    }
    window.setTimeout(() => {
      try {
        if (recorder.state === "recording") recorder.stop();
      } catch {
        done();
      }
    }, 120);
    window.setTimeout(done, 600);
  });
  utteranceRecorder = null;
}

function resampleLinear(input: Float32Array, inputRate: number, outputRate: number): Float32Array {
  if (inputRate === outputRate) return input;
  const ratio = inputRate / outputRate;
  const length = Math.max(1, Math.floor(input.length / ratio));
  const output = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const pos = i * ratio;
    const idx0 = Math.floor(pos);
    const idx1 = Math.min(idx0 + 1, input.length - 1);
    const frac = pos - idx0;
    output[i] = input[idx0] * (1 - frac) + input[idx1] * frac;
  }
  return output;
}

function float32ToInt16(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const v = Math.max(-1, Math.min(1, input[i]));
    out[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  return out;
}

function sendPcmFrame(samples: Int16Array) {
  if (!wsClient || !capturingUtterance) return;
  if (samples.length <= 0) return;
  pcmSentBytes += samples.byteLength;
  if (latencyDebug && latFirstUpFrameAt === 0 && latSpeechStartAt > 0) {
    latFirstUpFrameAt = performance.now();
    console.log("[latency] first_up_frame_ms", (latFirstUpFrameAt - latSpeechStartAt).toFixed(1));
  }
  const blob = new Blob([samples.buffer.slice(0)], { type: recorderMimeType.value });
  void wsClient.sendVoiceChunk(blob, recorderMimeType.value);
}

function flushPcmPending(force: boolean) {
  const frameSamples = Math.floor(pcmAsrSampleRate / 10);
  while (pcmPendingSamples.length >= frameSamples) {
    const frame = pcmPendingSamples.splice(0, frameSamples);
    sendPcmFrame(Int16Array.from(frame));
  }
  if (force && pcmPendingSamples.length > 0) {
    sendPcmFrame(Int16Array.from(pcmPendingSamples.splice(0, pcmPendingSamples.length)));
  }
}

function startPcmRecorder() {
  stopPcmRecorder();
  if (!mediaStream || !wsClient) return;
  const AudioContextCtor = window.AudioContext || (window as any).webkitAudioContext;
  const ctx: AudioContext = new AudioContextCtor();
  pcmAudioContext = ctx;
  pcmSourceNode = ctx.createMediaStreamSource(mediaStream);
  pcmProcessor = ctx.createScriptProcessor(4096, 1, 1);
  pcmSilenceGain = ctx.createGain();
  pcmSilenceGain.gain.value = 0;
  pcmProcessor.onaudioprocess = (evt) => {
    if (!capturingUtterance || !wsClient) return;
    const input = evt.inputBuffer.getChannelData(0);
    const resampled = resampleLinear(input, ctx.sampleRate, pcmAsrSampleRate);
    const int16 = float32ToInt16(resampled);
    for (let i = 0; i < int16.length; i++) pcmPendingSamples.push(int16[i]);
    flushPcmPending(false);
  };
  pcmSourceNode.connect(pcmProcessor);
  pcmProcessor.connect(pcmSilenceGain);
  pcmSilenceGain.connect(ctx.destination);
}

function stopPcmRecorder() {
  if (pcmProcessor) {
    try {
      pcmProcessor.disconnect();
    } catch {
    }
  }
  if (pcmSourceNode) {
    try {
      pcmSourceNode.disconnect();
    } catch {
    }
  }
  if (pcmSilenceGain) {
    try {
      pcmSilenceGain.disconnect();
    } catch {
    }
  }
  pcmProcessor = null;
  pcmSourceNode = null;
  pcmSilenceGain = null;
  if (pcmAudioContext) {
    try {
      void pcmAudioContext.close();
    } catch {
    }
  }
  pcmAudioContext = null;
}

async function flushPcmRecorder(): Promise<void> {
  await new Promise((resolve) => window.setTimeout(resolve, 80));
  flushPcmPending(true);
  stopPcmRecorder();
}

async function startAlwaysOnMic() {
  if (!wsClient || micStarted) return;
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    micStarted = true;

    const vadConfig = loadVadConfig();
    vadMonitor = new EnergyVadMonitor(vadConfig, {
      onSpeechStart: () => {
        if (manualSpeakActive) return;
        beginUtteranceCapture();
      },
      onSpeechCancel: () => {
        if (manualSpeakActive) return;
        cancelUtteranceCapture();
      },
      onSpeechEnd: () => {
        if (manualSpeakActive) return;
        void finishUtteranceAndCommit();
      },
    });
    vadMonitor.start(mediaStream);
    vadMonitor.resumeAudio();
  } catch {
    micStarted = false;
    error.value = "无法访问麦克风，请检查浏览器权限";
    connectionState.value = "failed";
    micHint.value = "麦克风未授权，请点击页面任意处后重试";
  }
}

async function uploadUtteranceBlob(): Promise<boolean> {
  if (!wsClient) return false;
  if (pcmAsrEnabled) return pcmSentBytes > 0;
  const chunks = utteranceChunks.splice(0, utteranceChunks.length);
  if (!chunks.length) return false;
  wsClient.resetUtterance();
  const blob = new Blob(chunks, { type: recorderMimeType.value || "audio/webm" });
  await wsClient.sendVoiceChunk(blob, recorderMimeType.value);
  return blob.size > 0;
}

async function finishUtteranceAndCommit() {
  if (!utteranceActive && !capturingUtterance) return;
  utteranceActive = false;
  userSpeaking.value = false;
  partialAsr.value = "";

  if (loading.value || openingInProgress) {
    cancelUtteranceCapture();
    return;
  }

  await flushUtteranceRecorder();
  await new Promise((resolve) => window.setTimeout(resolve, 120));
  capturingUtterance = false;

  const uploaded = await uploadUtteranceBlob();
  if (!uploaded) {
    softHint.value = "没录到声音，请按住 🎙 说话或检查麦克风";
    window.setTimeout(() => {
      softHint.value = "";
    }, 2500);
    return;
  }
  if (!wsClient) return;
  commitCurrentUtterance();
}

function commitCurrentUtterance() {
  if (!wsClient || loading.value) return;
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
  stopUtteranceRecorder();
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  userSpeaking.value = false;
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
    if (ttsAudioQueue.length === 0 && ttsQueue.length === 0) {
      const idle = playbackIdleCallback;
      playbackIdleCallback = null;
      idle?.();
    }
    if (!ttsSpeaking && ttsQueue.length === 0 && !loading.value && !openingInProgress) {
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

function enqueueBackendTtsAudio(audioB64: string, mimeType: string, onIdle?: () => void) {
  if (!ttsEnabled || !audioB64 || (isStaleTurn() && !openingInProgress)) {
    onIdle?.();
    return;
  }
  if (onIdle) playbackIdleCallback = onIdle;
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
    if (ttsAudioQueue.length === 0) {
      const idle = playbackIdleCallback;
      playbackIdleCallback = null;
      idle?.();
    }
    if (ttsAudioQueue.length === 0 && !loading.value && !isStaleTurn() && !openingInProgress) {
      callPhase.value = "listening";
    }
    playBackendTtsQueue();
  };
  audio.onended = finish;
  audio.onerror = finish;
  void audio.play().catch(finish);
}
</script>

<style scoped>
.page-root { width: 375px; height: 700px; }
.phone-shell { width: 100%; height: 100%; border-radius: 32px; overflow: hidden; position: relative; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a; background: #fff; }
.phone-notch { position: absolute; top: 8px; left: 50%; transform: translateX(-50%); width: 100px; height: 24px; background: #1a1a1a; border-radius: 0 0 16px 16px; z-index: 10; }
.status-bar { height: 36px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0; }
.status-bar.dark { background: #1a1a2e; }
.call-active-bg { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%); flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; align-items: center; padding: 20px 24px; position: relative; color: #fff; }
.call-avatar-large { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; margin-top: 20px; transition: box-shadow 0.3s ease; background: #f0f0f0; }
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
.call-btn-ptt { background: #00c2a2; font-size: 20px; }
.call-btn-ptt.active { background: #00a88a; box-shadow: 0 0 0 4px rgba(0, 194, 162, 0.35); }
.call-btn-mute { width: 48px; height: 48px; font-size: 18px; background: rgba(255,255,255,0.15); }
.error { color: #ff9aa2; font-size: 12px; margin-top: 4px; text-align: center; }
</style>
