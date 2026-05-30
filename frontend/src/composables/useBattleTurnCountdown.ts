import { computed, onUnmounted, ref } from "vue";

const DEFAULT_SECONDS = 10;

export function useBattleTurnCountdown(totalSeconds = DEFAULT_SECONDS) {
  const durationMs = ref(totalSeconds * 1000);
  const remainingMs = ref(totalSeconds * 1000);
  const isRunning = ref(false);
  let rafId = 0;
  let lastTick = 0;

  const progressPercent = computed(() =>
    Math.max(0, Math.min(100, (remainingMs.value / durationMs.value) * 100)),
  );

  const remainingSeconds = computed(() => Math.max(0, Math.ceil(remainingMs.value / 1000)));

  const isUrgent = computed(() => isRunning.value && remainingMs.value <= 3000);

  function stopLoop() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
  }

  function tick(now: number) {
    if (!isRunning.value) return;
    const delta = now - lastTick;
    lastTick = now;
    remainingMs.value = Math.max(0, remainingMs.value - delta);
    if (remainingMs.value <= 0) {
      isRunning.value = false;
      stopLoop();
      return;
    }
    rafId = requestAnimationFrame(tick);
  }

  function reset(seconds = totalSeconds) {
    stopLoop();
    durationMs.value = seconds * 1000;
    remainingMs.value = seconds * 1000;
    isRunning.value = true;
    lastTick = performance.now();
    rafId = requestAnimationFrame(tick);
  }

  function pause() {
    isRunning.value = false;
    stopLoop();
  }

  onUnmounted(stopLoop);

  return {
    progressPercent,
    remainingSeconds,
    isUrgent,
    isRunning,
    reset,
    pause,
  };
}
