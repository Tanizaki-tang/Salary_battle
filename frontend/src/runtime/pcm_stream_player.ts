export class PcmStreamPlayer {
  private ctx: AudioContext;
  private nextTime = 0;
  private stopped = false;

  constructor() {
    this.ctx = new AudioContext();
  }

  stop() {
    this.stopped = true;
    this.nextTime = 0;
    try {
      void this.ctx.close();
    } catch {
      /* ignore */
    }
  }

  playPcm16Base64(b64: string, sampleRate: number) {
    if (this.stopped) return;
    const bytes = base64ToBytes(b64);
    const pcm16 = new Int16Array(bytes.buffer, bytes.byteOffset, Math.floor(bytes.byteLength / 2));
    this.playPcm16(pcm16, sampleRate);
  }

  playPcm16(pcm16: Int16Array, sampleRate: number) {
    if (this.stopped) return;
    if (pcm16.length === 0) return;

    const buffer = this.ctx.createBuffer(1, pcm16.length, sampleRate);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < pcm16.length; i++) {
      channel[i] = pcm16[i] / 32768;
    }

    const source = this.ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.ctx.destination);

    const now = this.ctx.currentTime;
    const startAt = Math.max(now + 0.02, this.nextTime || now + 0.02);
    source.start(startAt);
    this.nextTime = startAt + buffer.duration;
  }
}

function base64ToBytes(b64: string) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

