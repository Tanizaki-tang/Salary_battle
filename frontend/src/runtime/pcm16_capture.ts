export type Pcm16CaptureHandlers = {
  onFrame: (pcm16: Int16Array, sampleRate: number) => void;
};

export class Pcm16MicrophoneCapture {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private stopped = true;
  private readonly targetRate: number;
  private readonly frameMs: number;
  private handlers: Pcm16CaptureHandlers | null = null;
  private pending: Float32Array = new Float32Array(0);

  constructor(targetRate = 16000, frameMs = 40) {
    this.targetRate = targetRate;
    this.frameMs = frameMs;
  }

  async start(handlers: Pcm16CaptureHandlers) {
    if (!this.stopped) return;
    this.stopped = false;
    this.handlers = handlers;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const ctx = new AudioContext();
    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(2048, 1, 1);

    processor.onaudioprocess = (e) => {
      if (this.stopped) return;
      const input = e.inputBuffer.getChannelData(0);
      this.enqueue(input, ctx.sampleRate);
    };

    source.connect(processor);
    processor.connect(ctx.destination);

    this.stream = stream;
    this.ctx = ctx;
    this.source = source;
    this.processor = processor;
  }

  stop() {
    this.stopped = true;
    this.handlers = null;
    this.pending = new Float32Array(0);

    try {
      this.processor?.disconnect();
    } catch {
      /* ignore */
    }
    try {
      this.source?.disconnect();
    } catch {
      /* ignore */
    }

    for (const t of this.stream?.getTracks() || []) t.stop();
    this.stream = null;
    this.processor = null;
    this.source = null;

    void this.ctx?.close();
    this.ctx = null;
  }

  private enqueue(input: Float32Array, inputRate: number) {
    const merged = new Float32Array(this.pending.length + input.length);
    merged.set(this.pending, 0);
    merged.set(input, this.pending.length);
    this.pending = merged;

    const targetSamplesPerFrame = Math.max(1, Math.floor((this.targetRate * this.frameMs) / 1000));
    const inputSamplesPerFrame = Math.max(1, Math.floor((inputRate * this.frameMs) / 1000));

    while (this.pending.length >= inputSamplesPerFrame) {
      const chunk = this.pending.subarray(0, inputSamplesPerFrame);
      const rest = this.pending.subarray(inputSamplesPerFrame);
      this.pending = new Float32Array(rest.length);
      this.pending.set(rest, 0);

      const down = downsampleFloat32(chunk, inputRate, this.targetRate, targetSamplesPerFrame);
      const pcm16 = floatToPcm16(down);
      this.handlers?.onFrame(pcm16, this.targetRate);
    }
  }
}

function downsampleFloat32(
  input: Float32Array,
  inputRate: number,
  targetRate: number,
  targetLength: number,
) {
  if (inputRate === targetRate) return input;
  const ratio = inputRate / targetRate;
  const out = new Float32Array(targetLength);
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      sum += input[j];
      count++;
    }
    out[i] = count > 0 ? sum / count : 0;
  }
  return out;
}

function floatToPcm16(input: Float32Array) {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? Math.round(s * 32768) : Math.round(s * 32767);
  }
  return out;
}

