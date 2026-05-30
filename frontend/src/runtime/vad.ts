export type VadPhase = "calibrating" | "idle" | "pending" | "speaking" | "silence";

export type VadConfig = {
  threshold: number;
  silenceMs: number;
  minSpeechMs: number;
  pollIntervalMs: number;
  attackMs: number;
  calibrationMs: number;
  noiseMultiplier: number;
  hysteresisRatio: number;
};

export type VadCallbacks = {
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onSpeechCancel?: () => void;
  onCalibrated?: (noiseFloor: number, startThreshold: number) => void;
  onEnergy?: (level: number, phase: VadPhase) => void;
};

function readEnvNumber(key: string, fallback: number): number {
  const raw = (import.meta.env[key] as string | undefined)?.trim();
  if (!raw) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

export function loadVadConfig(): VadConfig {
  return {
    threshold: readEnvNumber("VITE_VAD_THRESHOLD", 0.022),
    silenceMs: readEnvNumber("VITE_VAD_SILENCE_MS", 900),
    minSpeechMs: readEnvNumber("VITE_VAD_MIN_SPEECH_MS", 500),
    pollIntervalMs: readEnvNumber("VITE_VAD_POLL_MS", 50),
    attackMs: readEnvNumber("VITE_VAD_ATTACK_MS", 280),
    calibrationMs: readEnvNumber("VITE_VAD_CALIBRATION_MS", 900),
    noiseMultiplier: readEnvNumber("VITE_VAD_NOISE_MULTIPLIER", 3.2),
    hysteresisRatio: readEnvNumber("VITE_VAD_HYSTERESIS", 0.62),
  };
}

export class EnergyVadMonitor {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private timer: number | null = null;
  private phase: VadPhase = "calibrating";
  private speechStartedAt = 0;
  private silenceStartedAt = 0;
  private pendingStartedAt = 0;
  private calibrationStartedAt = 0;
  private calibrationSamples: number[] = [];
  private noiseFloor = 0;
  private startThreshold = 0;
  private endThreshold = 0;
  private readonly config: VadConfig;
  private readonly callbacks: VadCallbacks;
  private enabled = true;

  constructor(config: VadConfig, callbacks: VadCallbacks = {}) {
    this.config = config;
    this.callbacks = callbacks;
  }

  start(stream: MediaStream): void {
    this.stop();
    this.audioContext = new AudioContext();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 512;
    this.analyser.smoothingTimeConstant = 0.82;
    this.source = this.audioContext.createMediaStreamSource(stream);
    this.source.connect(this.analyser);
    this.phase = "calibrating";
    this.speechStartedAt = 0;
    this.silenceStartedAt = 0;
    this.pendingStartedAt = 0;
    this.calibrationStartedAt = Date.now();
    this.calibrationSamples = [];
    this.noiseFloor = 0;
    this.startThreshold = this.config.threshold;
    this.endThreshold = this.config.threshold * this.config.hysteresisRatio;
    this.enabled = true;
    this.timer = window.setInterval(() => this.tick(), this.config.pollIntervalMs);
  }

  stop(): void {
    if (this.timer !== null) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
    this.source?.disconnect();
    this.source = null;
    this.analyser = null;
    if (this.audioContext) {
      void this.audioContext.close();
      this.audioContext = null;
    }
    this.phase = "idle";
  }

  setEnabled(value: boolean): void {
    this.enabled = value;
    if (!value) {
      this.resetToIdle();
    }
  }

  private resetToIdle(): void {
    this.phase = "idle";
    this.speechStartedAt = 0;
    this.silenceStartedAt = 0;
    this.pendingStartedAt = 0;
  }

  private readLevel(): number {
    if (!this.analyser) return 0;
    const data = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      const v = (data[i] - 128) / 128;
      sum += v * v;
    }
    return Math.sqrt(sum / data.length);
  }

  private finishCalibration(level: number): void {
    this.calibrationSamples.push(level);
    const sorted = [...this.calibrationSamples].sort((a, b) => a - b);
    const idx = Math.min(sorted.length - 1, Math.floor(sorted.length * 0.85));
    this.noiseFloor = sorted[idx] ?? level;
    const adaptive = this.noiseFloor * this.config.noiseMultiplier;
    this.startThreshold = Math.max(this.config.threshold, adaptive);
    this.endThreshold = this.startThreshold * this.config.hysteresisRatio;
    this.phase = "idle";
    this.callbacks.onCalibrated?.(this.noiseFloor, this.startThreshold);
  }

  private cancelSpeech(): void {
    this.resetToIdle();
    this.callbacks.onSpeechCancel?.();
  }

  private confirmSpeech(now: number): void {
    this.phase = "speaking";
    this.speechStartedAt = now;
    this.silenceStartedAt = 0;
    this.pendingStartedAt = 0;
    this.callbacks.onSpeechStart?.();
  }

  private tick(): void {
    if (!this.enabled || !this.analyser) return;
    const level = this.readLevel();
    const now = Date.now();

    if (this.phase === "calibrating") {
      this.calibrationSamples.push(level);
      if (now - this.calibrationStartedAt >= this.config.calibrationMs) {
        this.finishCalibration(level);
      }
      this.callbacks.onEnergy?.(level, this.phase);
      return;
    }

    const aboveStart = level >= this.startThreshold;
    const aboveEnd = level >= this.endThreshold;

    if (this.phase === "idle") {
      if (aboveStart) {
        this.phase = "pending";
        this.pendingStartedAt = now;
      }
      this.callbacks.onEnergy?.(level, this.phase);
      return;
    }

    if (this.phase === "pending") {
      if (!aboveStart) {
        this.phase = "idle";
        this.pendingStartedAt = 0;
      } else if (now - this.pendingStartedAt >= this.config.attackMs) {
        this.confirmSpeech(now);
      }
      this.callbacks.onEnergy?.(level, this.phase);
      return;
    }

    if (this.phase === "speaking") {
      if (!aboveEnd) {
        this.phase = "silence";
        this.silenceStartedAt = now;
      }
      this.callbacks.onEnergy?.(level, this.phase);
      return;
    }

    if (this.phase === "silence") {
      if (aboveStart) {
        this.phase = "speaking";
        this.silenceStartedAt = 0;
        this.callbacks.onEnergy?.(level, this.phase);
        return;
      }

      const silenceDuration = now - this.silenceStartedAt;
      const speechDuration = this.silenceStartedAt - this.speechStartedAt;
      if (silenceDuration >= this.config.silenceMs) {
        if (speechDuration >= this.config.minSpeechMs) {
          this.resetToIdle();
          this.callbacks.onSpeechEnd?.();
        } else {
          this.cancelSpeech();
        }
      }
      this.callbacks.onEnergy?.(level, this.phase);
    }
  }
}
