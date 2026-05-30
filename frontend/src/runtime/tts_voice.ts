export type TtsVoiceConfig = {
  rate: number;
  pitch: number;
  volume: number;
  preferredName: string;
};

const STRONG_BREAK = /[。！？.!?]/;

export function loadTtsVoiceConfig(): TtsVoiceConfig {
  const rate = Number(import.meta.env.VITE_TTS_RATE ?? "0.92");
  const pitch = Number(import.meta.env.VITE_TTS_PITCH ?? "1.02");
  const volume = Number(import.meta.env.VITE_TTS_VOLUME ?? "1");
  return {
    rate: Number.isFinite(rate) ? rate : 0.92,
    pitch: Number.isFinite(pitch) ? pitch : 1.02,
    volume: Number.isFinite(volume) ? volume : 1,
    preferredName: String(import.meta.env.VITE_TTS_VOICE_NAME || "").trim(),
  };
}

export function ensureTtsVoices(): Promise<SpeechSynthesisVoice[]> {
  if (!("speechSynthesis" in window)) return Promise.resolve([]);
  const synth = window.speechSynthesis;
  const existing = synth.getVoices();
  if (existing.length > 0) return Promise.resolve(existing);

  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve(synth.getVoices());
    };
    synth.onvoiceschanged = finish;
    window.setTimeout(finish, 800);
  });
}

function scoreVoice(voice: SpeechSynthesisVoice, preferredName: string): number {
  const name = voice.name.toLowerCase();
  const lang = voice.lang.toLowerCase();
  if (!lang.startsWith("zh") && !name.includes("chinese") && !name.includes("mandarin")) {
    return -1;
  }
  if (preferredName && voice.name.includes(preferredName)) {
    return 1000;
  }

  let score = 0;
  if (name.includes("xiaoxiao") || name.includes("xiaoyi") || name.includes("yunxi")) score += 40;
  if (name.includes("huihui") || name.includes("kangkang")) score += 25;
  if (name.includes("natural") || name.includes("neural") || name.includes("online")) score += 30;
  if (name.includes("microsoft")) score += 15;
  if (name.includes("google")) score += 10;
  if (voice.localService) score += 8;
  if (lang === "zh-cn") score += 12;
  return score;
}

export function pickChineseVoice(
  voices: SpeechSynthesisVoice[],
  preferredName = "",
): SpeechSynthesisVoice | null {
  const ranked = voices
    .map((voice) => ({ voice, score: scoreVoice(voice, preferredName) }))
    .filter((item) => item.score >= 0)
    .sort((a, b) => b.score - a.score);
  return ranked[0]?.voice ?? null;
}

export function shouldFlushTtsBuffer(buffer: string, chunk: string): boolean {
  const text = (buffer || "").trim();
  if (!text) return false;
  if (STRONG_BREAK.test(chunk)) return true;
  return text.length >= 36;
}

export function createUtterance(text: string, voice: SpeechSynthesisVoice | null, cfg: TtsVoiceConfig): SpeechSynthesisUtterance {
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = voice?.lang || "zh-CN";
  utter.rate = cfg.rate;
  utter.pitch = cfg.pitch;
  utter.volume = cfg.volume;
  if (voice) utter.voice = voice;
  return utter;
}
