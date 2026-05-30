<template>
  <div class="turn-timer" :class="{ urgent: isUrgent, idle: !isRunning }">
    <div class="turn-timer-row">
      <span class="turn-timer-title">回复倒计时</span>
      <span class="turn-timer-val">{{ remainingSeconds }}s</span>
    </div>
    <div class="turn-timer-track" role="progressbar" :aria-valuenow="remainingSeconds" aria-valuemin="0" :aria-valuemax="10">
      <div class="turn-timer-fill" :style="{ width: `${progressPercent}%` }" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  progressPercent: number;
  remainingSeconds: number;
  isUrgent: boolean;
  isRunning: boolean;
}>();
</script>

<style scoped>
.turn-timer {
  padding: 8px 16px 6px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.turn-timer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.turn-timer-title {
  font-size: 11px;
  color: #888;
  font-weight: 600;
}

.turn-timer-val {
  font-size: 12px;
  font-weight: 700;
  color: #ff4757;
  font-variant-numeric: tabular-nums;
}

.turn-timer-track {
  height: 6px;
  border-radius: 999px;
  background: #ffe8ea;
  overflow: hidden;
}

.turn-timer-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff6b81, #ff4757);
  transition: width 0.08s linear;
  box-shadow: 0 0 8px rgba(255, 71, 87, 0.35);
}

.turn-timer.urgent .turn-timer-fill {
  background: linear-gradient(90deg, #ff4757, #c0392b);
  animation: timerPulse 0.65s ease-in-out infinite;
}

.turn-timer.urgent .turn-timer-val {
  animation: timerPulse 0.65s ease-in-out infinite;
}

.turn-timer.idle .turn-timer-fill {
  width: 0 !important;
  box-shadow: none;
}

@keyframes timerPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.72; }
}
</style>
